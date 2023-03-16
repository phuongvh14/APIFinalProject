from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.contrib.auth.models import User, Group
from rest_framework import generics, viewsets, status
from .serializers import UserSerializer, MenuItemSerializer, CartSerializer, DeliveryCrewOrderSerializer, OrderSerializer, CategorySerializer
from .models import MenuItem, Cart, Order, OrderItem, Category
from .permissions import ManagersOnly
from datetime import datetime   


# Viewsets for user group management, 1 for managers and 1 for delivery crews
class UserGroupViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser, ManagersOnly]
    
    # Listing all the managers
    def list(self, request):
        query = User.objects.all().filter(groups__name='Manager')
        managers = UserSerializer(query, many=True)  # Passing many=True means that query will not be a single instance object
        return Response(managers.data)
        
    def create(self, request):
        to_add = get_object_or_404(User, username=request.data.get('username'))
        all_managers = Group.objects.get(name='Manager')
        all_managers.user_set.add(to_add)
        return Response({'message': f'{to_add.username} has been added to the manager group'}, status.HTTP_201_CREATED)

    def destroy(self, request, pk):
        to_delete = get_object_or_404(User, pk=pk)
        all_managers = Group.objects.get(name='Manager')
        all_managers.user_set.remove(to_delete)
        return Response({'message': f'{to_delete.username} has been deleted from the manager group'}, status.HTTP_200_OK)


class DeliveryCrewManagementViewset(viewsets.ViewSet):
    permission_classes = [IsAdminUser, ManagersOnly]

    # Listing all the delivery crew
    def list(self, request):
        query = User.objects.all().filter(groups__name='Delivery-crew')
        delivery_crew = UserSerializer(query, many=True)
        return Response(delivery_crew.data)

    # Adding existing employee to delivery crew
    def create(self, request):
        to_add = get_object_or_404(User, username=request.data.get('username'))
        delivery_crew = Group.objects.get(name='Delivery-crew')
        delivery_crew.user_set.add(to_add)
        return Response({'message': f'{to_add.username} has been added to the delivery crew'}, status.HTTP_201_CREATED)

    # Removing an employee from the delivery crew
    def destroy(self, request, pk):
        to_delete = get_object_or_404(User, pk=pk)
        delivery_crew = Group.objects.get(name='Delivery-crew')
        delivery_crew.user_set.remove(to_delete)
        return Response({'message': f'{to_delete.username} has been deleted from the delivery crew'}, status.HTTP_200_OK)


# Menu-item views
class MenuItemView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    search_fields = ['category__title']
    ordering_fields = ['price']

    def get_permissions(self):
        permission_classes = []

        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated, ManagersOnly]
        return [permission() for permission in permission_classes]


# Single-menu-item views
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        permission_classes = []

        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated, ManagersOnly]
        return [permission() for permission in permission_classes]


# Cart management endpoints
class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    # Overidding the current queryset to get only results about current authenticated user
    def get_queryset(self):
        return Cart.objects.all().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        Cart.objects.all().filter(user=self.request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Order Management endpoints
class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Customers, who belongs to no group, can only see their orders
        if self.request.user.groups.count() == 0:
            return Order.objects.all().filter(user=self.request.user)
        
        # Delivery crew can only see assigned orders
        elif self.request.user.groups.filter(name='Delivery-crew').exists():
            return Order.objects.all().filter(delivery_crew=self.request.user)

        # Other authenticated users can only be managers and superuser
        else:
            return Order.objects.all()

    # Post method for customers with items in their cart
    def create(self, request, *args, **kwargs):
        cart_items = Cart.objects.all().filter(user=self.request.user)
        if len(cart_items) == 0:
            return Response({'message': 'There are currently no items in your cart'})
        
        # Prepping the data
        current_time = datetime.now().strftime("%Y-%m-%d")
        data = request.data.copy()
        data['user'] = self.request.user.pk
        data['date'] = current_time
        data['total'] = 0

        serializer = OrderSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        order = serializer.save()
        total = 0

        for item in cart_items.values():
            total += item['price']
            order_item = OrderItem(
                order = order,
                menuitem_id=item['menuitem_id'],
                price=item['price'],
                unit_price=item['unit_price'],
                quantity=item['quantity'],
            )
            order_item.save()

        # After saving all order items from cart, we empty the cart
        Cart.objects.all().filter(user=self.request.user).delete()

        # After saving all the order items, we update the total
        serializer = OrderSerializer(order, data={'total': total}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    
        return Response(serializer.data)


class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    # serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    
    # Making sure that delivery crew can only update the status of an order
    def get_serializer_class(self):
        if self.request.user.groups.filter(name='Delivery-crew').exists():
            return DeliveryCrewOrderSerializer
        return OrderSerializer


    def get_object(self):
        pk = self.kwargs.get('pk')
        # For customers:
        if self.request.user.groups.count() == 0:
            order = get_object_or_404(Order, user=self.request.user, pk=pk)
        # For managers and admin user:
        elif self.request.user.groups.filter(name='Manager').exists() or self.request.user.is_superuser:
            order = get_object_or_404(Order, pk=pk)
        # Delivery crew:
        elif self.request.user.groups.filter(name='Delivery-crew').exists():
           order = get_object_or_404(Order, delivery_crew=self.request.user, pk=pk)

        return order

    def update(self, request, *args, **kwargs):
        if self.request.user.groups.count() == 0:
            return Response({'message': 'You are not allowed to update this order once submitted'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return super().update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name='Manager').exists():
            return super().delete(request, *args, **kwargs)
        return Response({'message': 'You are not allowed to delete an order'}, status=status.HTTP_401_UNAUTHORIZED)
        

# Category view
class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method != 'GET':
            permission_classes = [IsAuthenticated, ManagersOnly]

        return [permission() for permission in permission_classes]

















