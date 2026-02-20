import React, { useEffect, useState, useContext } from 'react';
import { fetchOrders } from '../services/OrderService'; 
import { ShopContext } from '../context/ShopContext';
import Title from '../components/Title';
import { fetchAuthSession } from 'aws-amplify/auth';
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);


const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { currency } = useContext(ShopContext);

  useEffect(() => {
    const getOrders = async () => {
      try {
        const { tokens } = await fetchAuthSession();

        // Get user attributes from the ID token
        const payload = tokens.idToken.payload;
        const tenantId = payload['custom:tenantName'];
        
        console.log('Fetching orders for tenant:', tenantId);
        const ordersData = await fetchOrders(tenantId);

        // Sort orders by descending order of orderDate
        const sortedOrders = ordersData.sort((a, b) => {
          const dateA = dayjs(a.orderDate, 'DD/MM/YYYY hh:mm A');
          const dateB = dayjs(b.orderDate, 'DD/MM/YYYY hh:mm A');
          return dateB - dateA;
        });
                setOrders(sortedOrders);
      } catch (error) {
        setError('Failed to fetch orders');
        console.error('Error fetching orders:', error);
      } finally {
        setLoading(false);
      }
    };

    getOrders();
  }, []);

  if (loading) {
    return (
      <div className="py-8 text-center">
        <p>Loading orders...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8 text-center text-red-500">
        <p>{error}</p>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="py-8 text-center">
        <p>No orders found</p>
      </div>
    );
  } 

  return (
    <div className="border-t pt-16">
      <div className="text-2xl">
        <Title text1={'MY'} text2={'ORDERS'} />
      </div>

      {/* Order Table */}
      <div className="overflow-x-auto mt-8">
        <table className="w-full border-collapse border border-gray-300">
          <thead>
            <tr className="bg-gray-100 text-gray-700 text-left">
              <th className="p-3 border">Order ID</th>
              <th className="p-3 border">Product</th>
              <th className="p-3 border">Price</th>
              <th className="p-3 border">Order Date</th>
              <th className="p-3 border">Status</th>
              <th className="p-3 border">Rating</th>
              <th className="p-3 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id} className="border hover:bg-gray-50 transition">
                <td className="p-3 border text-gray-700">{order.id}</td>
                <td className="p-3 border font-medium">{order.productName}</td>
                <td className="p-3 border">{currency}{order.price}</td>
                <td className="p-3 border text-gray-500">{order.orderDate}</td>
                <td className="p-3 border">
                  <span
                    className={`px-3 py-1 text-sm font-semibold rounded ${
                      order.status === 'Delivered'
                        ? 'bg-green-200 text-green-700'
                        : order.status === 'Dispatched'
                        ? 'bg-blue-200 text-blue-700'
                        : order.status === 'Returned'
                        ? 'bg-red-200 text-red-700'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {order.status}
                  </span>
                </td>
                <td className="p-3 border">
                  {/* Render the correct number of stars dynamically */}
                  {'⭐'.repeat(order.rating)}
                </td>
                <td className="p-3 border">
                  <button className="bg-blue-500 text-white px-4 py-2 text-sm rounded hover:bg-blue-600 transition">
                    Track Order
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Example OrderList Component
const OrderList = ({ orders }) => {
  return (
    <div className="order-list">
      {orders.length === 0 ? (
        <p className="text-gray-500 text-center">
          You don't have any orders yet.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {orders.map(order => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </div>
  );
};

export default Orders;
