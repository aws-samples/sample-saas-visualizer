import React from 'react';
import { Typography, Button } from '@mui/material';

const Cart = () => {
  return (
    <div>
      <Typography variant="h5">Shopping Cart</Typography>
      <Typography>No items in cart yet.</Typography>
      <Button variant="contained" color="secondary">Proceed to Checkout</Button>
    </div>
  );
};

export default Cart;
