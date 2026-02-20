import axios from 'axios';
import { fetchAuthSession } from "aws-amplify/auth"; // Use fetchAuthSession
import { v4 as uuidv4 } from 'uuid'; // Import UUID for generating unique IDs

const API_URL = window.APP_CONFIG.api.dataAccessUrl;
const SHARED_QUEUE_API_URL = window.APP_CONFIG.api.orderSharedQueueUrl;
const SILOED_QUEUE_API_URL = window.APP_CONFIG.api.orderSiloedQueueUrl;

console.log('API_URL:', window.APP_CONFIG.api.dataAccessUrl);
console.log('SHARED_QUEUE_API_URL:', window.APP_CONFIG.api.orderSharedQueueUrl);
console.log('SILOED_QUEUE_API_URL:', window.APP_CONFIG.api.orderSiloedQueueUrl);

// Sample data to use when API fails
const sampleOrders = [
  {
    id: 'SAMPLE-001',
    productName: 'Sample Product 1',
    price: 99.99,
    orderDate: '2024-01-15',
    status: 'Delivered',
    rating: 4,
    image: '/images/default-product.png'
  },
  {
    id: 'SAMPLE-002',
    productName: 'Sample Product 2',
    price: 149.99,
    orderDate: '2024-01-14',
    status: 'Processing',
    rating: 5,
    image: '/images/default-product.png'
  },
  {
    id: 'SAMPLE-003',
    productName: 'Sample Product 3',
    price: 79.99,
    orderDate: '2024-01-13',
    status: 'Shipped',
    rating: 3,
    image: '/images/default-product.png'
  }
];

// Helper function to get Cognito token using fetchAuthSession
const getAuthToken = async () => {
  const session = await fetchAuthSession(); // Fetch the current session
  console.log("id token", session.tokens.idToken); // Log idToken
  console.log("access token", session.tokens.accessToken); // Log accessToken
  return session.tokens.idToken; // Return the idToken
};

export const fetchOrders = async (tenantId) => {
  try {
    const token = await getAuthToken(); // Get Cognito token

    const response = await axios.get(API_URL, {
      headers: {
        'Authorization': `Bearer ${token}`, // Add Authorization header
      },
    });

    // Return the orders if the API call is successful
    return response.data.map(order => ({
      id: order.ID,
      productName: order.Product,
      price: order.Price,
      orderDate: order.Order_Date,
      status: order.Status,
      rating: order.Rating,
      image: `/images/default-product.png`
    }));
  } catch (error) {
    console.error('Error fetching orders:', error);

    // Return an empty array if the API fails
    return [];
  }
};

// Helper function to build query string
const buildQueryString = (params) => {
  return Object.keys(params)
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
};

// Place an order using the shared queue API
export const placeOrderSharedQueue = async (order, MessageGroupId, MessageDeduplicationId) => {
  try {
    const token = await getAuthToken(); // Get Cognito token

    const response = await axios.put(SHARED_QUEUE_API_URL, order, {
      headers: {
        'Authorization': `Bearer ${token}`, // Add Authorization header
      },
    }); // Send order in the body
    return response.data;
  } catch (error) {
    console.error('Error placing order in shared queue:', error);
    throw error;
  }
};

// Place an order using the siloed queue API
export const placeOrderSiloedQueue = async (order, MessageGroupId, MessageDeduplicationId) => {
  try {
    const token = await getAuthToken(); // Get Cognito token

    const response = await axios.put(SILOED_QUEUE_API_URL, order, {
      headers: {
        'Authorization': `Bearer ${token}`, // Add Authorization header
      },
    }); // Send order in the body
    return response.data;
  } catch (error) {
    console.error('Error placing order in siloed queue:', error);
    throw error;
  }
};
