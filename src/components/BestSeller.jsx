import React, { useContext, useEffect, useState } from 'react';
import Title from './Title';
import { ShopContext } from '../context/ShopContext';
import ProductItem from './ProductItem';

const BestSeller = () => {
  const [bestSeller, setBestSeller] = useState([]);
  const { products } = useContext(ShopContext);

  useEffect(() => {
    const bestProduct = products.filter((item) => item.bestseller);
    setBestSeller(bestProduct.slice(0, 5));
  }, [products]);

  return (
    <div className="my-16 bg-white rounded-xl shadow-sm px-4 py-10">
      {/* Section Heading */}
      <div className="text-center mb-10">
        <Title text1="BEST" text2="SELLERS" />
        <p className="mt-2 text-sm sm:text-base text-gray-500 font-medium tracking-wide">
          Handpicked SaaS favorites across tenants
        </p>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
        {bestSeller.map((item, index) => (
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

export default BestSeller;
