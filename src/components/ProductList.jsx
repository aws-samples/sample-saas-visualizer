import React, { useState, useEffect } from 'react';
import { useTenant } from './TenantContext';
import { Card, CardContent, Typography, Button, Grid } from '@mui/material';

const productsData = {
  "Tenant A": [
    { id: 1, name: "Product 1A", price: 10 },
    { id: 2, name: "Product 2A", price: 15 }
  ],
  "Tenant B": [
    { id: 3, name: "Product 1B", price: 12 },
    { id: 4, name: "Product 2B", price: 18 }
  ],
  "Tenant C": [
    { id: 5, name: "Product 1C", price: 20 },
    { id: 6, name: "Product 2C", price: 25 }
  ]
};

const ProductList = () => {
  const { tenant } = useTenant();
  const [products, setProducts] = useState([]);

  useEffect(() => {
    setProducts(productsData[tenant] || []);
  }, [tenant]);

  return (
    <Grid container spacing={2}>
      {products.map((product) => (
        <Grid item xs={12} sm={6} md={4} key={product.id}>
          <Card>
            <CardContent>
              <Typography variant="h6">{product.name}</Typography>
              <Typography color="textSecondary">₹{product.price}</Typography>
              <Button variant="contained" color="primary">Add to Cart</Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default ProductList;
