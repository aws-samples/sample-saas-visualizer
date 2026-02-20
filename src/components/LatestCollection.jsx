import React, { useContext, useEffect, useState } from 'react';
import Title from './Title';
import { ShopContext } from '../context/ShopContext';
import ProductItem from './ProductItem';

const LatestCollection = () => {
  const [latestProducts, setLatestProducts] = useState([]);
  const { products } = useContext(ShopContext);

  useEffect(() => {
    if (products.length > 0) {
      setLatestProducts(products.slice(0, 10));
    }
  }, [products]);

  return (
    <div className="px-4 sm:px-10 py-16">
    <div className="text-center mb-10">
      <Title text1="LATEST" text2="COLLECTIONS" />
      <p className="mt-2 text-sm sm:text-base text-gray-500 font-medium tracking-wide">
        Multi-Tenant SaaS Product Showcase
      </p>
    </div>
  
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
      {latestProducts.map((item, index) => (
        <ProductItem
          key={index}
          id={item._id}
          image={item.image}
          name={item.name}
          price={item.price}
        />
      ))}
    </div>
  </div>
  
  );
};

export default LatestCollection;
