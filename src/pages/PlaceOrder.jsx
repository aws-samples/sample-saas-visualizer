import React, { useContext, useState, useEffect } from 'react';
import Title from '../components/Title';
import CartTotal from '../components/CartTotal';
import { assets } from '../assets/assets';
import { ShopContext } from '../context/ShopContext';
import { fetchAuthSession } from '@aws-amplify/auth';
import { placeOrderSharedQueue, placeOrderSiloedQueue } from '../services/OrderService';
import { v4 as uuidv4 } from 'uuid'; // Import UUID for unique IDs
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css'; // Import toast styles

const PlaceOrder = () => {
    const [method, setMethod] = useState('cod');
    const { navigate, cartItems, products, clearCart } = useContext(ShopContext); // Include clearCart from ShopContext
    const [queueType, setQueueType] = useState('shared'); // Toggle for queue type
    const [userDetails, setUserDetails] = useState({
        firstName: '',
        lastName: '',
        email: '',
        street: '',
        city: '',
        state: '',
        zipcode: '',
        country: '',
        phone: '',
    });
    const [tenantName, setTenantName] = useState(''); // Store tenant name

    const fetchUserDetails = async () => {
        try {
            const session = await fetchAuthSession();
            if (session?.tokens) {
                const { email, "custom:tenantName": tenantName } = session.tokens.idToken.payload;

                const [firstName = '', lastName = ''] = tenantName ? tenantName.split(' ') : [];

                setUserDetails((prevDetails) => ({
                    ...prevDetails,
                    firstName,
                    lastName,
                    email: email || '',
                }));

                setTenantName(tenantName || ''); // Set tenant name
            }
        } catch (error) {
            console.error('Error fetching user session:', error);
        }
    };

    const handlePlaceOrder = async () => {
        try {
            const MessageGroupId = uuidv4(); // Generate unique MessageGroupId for the entire order

            // Convert cartItems object into an array of items
            const cartItemsArray = Object.entries(cartItems).flatMap(([itemId, sizes]) =>
                Object.entries(sizes).map(([size, quantity]) => ({
                    itemId,
                    size,
                    quantity,
                }))
            );

            for (const cartItem of cartItemsArray) {
                const itemInfo = products.find((product) => product._id === cartItem.itemId); // Find product details
                if (!itemInfo) continue;

                const order = {
                    Product: `${itemInfo.name} (${cartItem.size})`, // Include size in product name
                    Price: itemInfo.price * cartItem.quantity, // Calculate total price for the item
                    Order_Date: (() => {
                        const now = new Date();
                        const day = String(now.getDate()).padStart(2, '0');
                        const month = String(now.getMonth() + 1).padStart(2, '0');
                        const year = now.getFullYear();
                        const hours = now.getHours();
                        const minutes = String(now.getMinutes()).padStart(2, '0');
                        const ampm = hours >= 12 ? 'PM' : 'AM';
                        const hours12 = hours % 12 || 12;
                        return `${day}/${month}/${year} ${String(hours12).padStart(2, '0')}:${minutes} ${ampm}`;
                    })(), // Current date and time in format dd/mm/yyyy hh:mm AM/PM
                    Status: 'Ordered', // Example status
                    Rating: Math.floor(Math.random() * (5 - 3 + 1)) + 3, // Random number between 3 and 5
                };

                const MessageDeduplicationId = uuidv4(); // Generate unique MessageDeduplicationId for each item

                if (queueType === 'shared') {
                    await placeOrderSharedQueue(order, MessageGroupId, MessageDeduplicationId);
                } else {
                    await placeOrderSiloedQueue(order, MessageGroupId, MessageDeduplicationId);
                }
            }

            // Clear the cart after successful order placement
            clearCart();

            toast.success('Order placed successfully!', {
                position: 'top-right',
                autoClose: 1000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
                draggable: true,
                progress: undefined,
            });

            // Removed navigation to orders page
        } catch (error) {
            console.error('Error placing order:', error);
            toast.error('Failed to place order. Please try again.', {
                position: 'top-right',
                autoClose: 3000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
                draggable: true,
                progress: undefined,
            });
        }
    };

    useEffect(() => {
        fetchUserDetails();
    }, []);

    return (
        <div className='flex flex-col sm:flex-row justify-between gap-4 pt-5 sm:pt-14 min-h-[80vh] border-t'>

            <div className='flex flex-col gap-4 w-full sm:max-w-[480px]'>

                <div className='text-xl sm:text-2xl my-3'>
                    <Title text1={'DELIVERY'} text2={'INFORMATION'} />
                </div>
                <div className='flex gap-3'>
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="text"
                        placeholder='First name'
                        value={userDetails.firstName}
                        onChange={(e) => setUserDetails({ ...userDetails, firstName: e.target.value })}
                    />
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="text"
                        placeholder='Last name'
                        value={userDetails.lastName}
                        onChange={(e) => setUserDetails({ ...userDetails, lastName: e.target.value })}
                    />
                </div>
                <input
                    className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                    type="email"
                    placeholder='Email address'
                    value={userDetails.email}
                    onChange={(e) => setUserDetails({ ...userDetails, email: e.target.value })}
                />
                <input
                    className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                    type="text"
                    placeholder='Street'
                    value={userDetails.street}
                    onChange={(e) => setUserDetails({ ...userDetails, street: e.target.value })}
                />
                <div className='flex gap-3'>
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="text"
                        placeholder='City'
                        value={userDetails.city}
                        onChange={(e) => setUserDetails({ ...userDetails, city: e.target.value })}
                    />
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="text"
                        placeholder='State'
                        value={userDetails.state}
                        onChange={(e) => setUserDetails({ ...userDetails, state: e.target.value })}
                    />
                </div>
                <div className='flex gap-3'>
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="number"
                        placeholder='Zipcode'
                        value={userDetails.zipcode}
                        onChange={(e) => setUserDetails({ ...userDetails, zipcode: e.target.value })}
                    />
                    <input
                        className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                        type="text"
                        placeholder='Country'
                        value={userDetails.country}
                        onChange={(e) => setUserDetails({ ...userDetails, country: e.target.value })}
                    />
                </div>
                <input
                    className='border border-gray-300 rounded py-1.5 px-3.5 w-full'
                    type="text"
                    placeholder='Phone'
                    value={userDetails.phone}
                    onChange={(e) => setUserDetails({ ...userDetails, phone: e.target.value })}
                />
            </div>

            <div className='mt-8'>

                <div className='mt-8 min-w-80'>
                    <CartTotal />
                </div>

                <div className='mt-12'>
                    <Title text1={'PAYMENT'} text2={'METHOD'} />
                    <div className='flex gap-3 flex-col lg:flex-row'>
                        <div onClick={() => setMethod('stripe')} className='flex items-center gap-3 border p-2 px-3 cursor-pointer'>
                            <p className={`min-w-3.5 h-3.5 border rounded-full ${method === 'stripe' ? 'bg-green-400' : ''}`}></p>
                            <img className='h-5 mx-4' src={assets.stripe_logo} alt="" />
                        </div>
                        <div onClick={() => setMethod('razorpay')} className='flex items-center gap-3 border p-2 px-3 cursor-pointer'>
                            <p className={`min-w-3.5 h-3.5 border rounded-full ${method === 'razorpay' ? 'bg-green-400' : ''}`}></p>
                            <img className='h-5 mx-4' src={assets.razorpay_logo} alt="" />
                        </div>
                        <div onClick={() => setMethod('cod')} className='flex items-center gap-3 border p-2 px-3 cursor-pointer'>
                            <p className={`min-w-3.5 h-3.5 border rounded-full ${method === 'cod' ? 'bg-green-400' : ''}`}></p>
                            <p className=' text-gray-500 text-sm font-medium mx-4'>CASH ON DELIVERY</p>
                        </div>
                    </div>
                    <div className='flex flex-col gap-4 mt-8'>
    <div className='flex gap-6'>
        <label className='flex items-center gap-2'>
            <input
                type="radio"
                name="queueType"
                value="shared"
                checked={queueType === 'shared'}
                onChange={() => setQueueType('shared')}
            />
            <span>Shared Queue</span>
        </label>
        <label className='flex items-center gap-2'>
            <input
                type="radio"
                name="queueType"
                value="siloed"
                checked={queueType === 'siloed'}
                onChange={() => setQueueType('siloed')}
            />
            <span>Siloed Queue</span>
        </label>
    </div>
    <button onClick={handlePlaceOrder} className='bg-black text-white px-16 py-3 text-sm'>PLACE ORDER</button>
</div>

                </div>

            </div>
            <ToastContainer />
        </div>
    );
};

export default PlaceOrder;
