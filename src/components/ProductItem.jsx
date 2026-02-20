import React, { useContext } from 'react';
import { ShopContext } from '../context/ShopContext';
import { Link } from 'react-router-dom';

const ProductItem = ({ id, image, name, price }) => {
  const { currency } = useContext(ShopContext);

  return (
    <Link
      to={`/product/${id}`}
      onClick={() => window.scrollTo(0, 0)}
      className="block bg-white rounded-xl shadow-md hover:shadow-lg transition duration-300 p-4"
    >
      <div className="overflow-hidden rounded-lg">
        <img
          className="w-full h-48 object-cover transform hover:scale-105 transition-transform duration-300"
          src={image[0]}
          alt={name}
        />
      </div>

      <div className="pt-4 text-center">
        <p className="text-base font-medium text-gray-800 mb-1">{name}</p>
        <p className="text-sm text-gray-600 font-semibold">
          {currency}
          {price}
        </p>
      </div>
    </Link>
  );
};

export default ProductItem;
