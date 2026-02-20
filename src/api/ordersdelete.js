import axios from 'axios';

// Replace this with your actual API Gateway endpoint
const API_URL = 'https://ud1l4z9zvi.execute-api.eu-west-1.amazonaws.com/data_access_stage';

export const fetchOrders = async (tenantId) => {
  try {
    const response = await axios.get(`${API_URL}?tenant=${tenantId}`);
    return response.data.map(order => ({
      id: order.ID,
      productName: order.Product,
      price: order.Price,
      orderDate: order.Order_Date,
      status: order.Status,
      rating: order.Rating,
      image: `/images/default-product.png` // Placeholder image, update if needed
    }));
  } catch (error) {
    console.error('Error fetching orders:', error);
    throw error;
  }
};
