import React from 'react';
import { assets } from '../assets/assets';

const Hero = () => {
return (
<div className="flex flex-col sm:flex-row bg-white rounded-xl overflow-hidden shadow-md mb-0 border border-gray-200">

{/* Hero Left Side */}
<div className="w-full sm:w-1/2 flex items-center justify-center px-6 py-12 sm:py-0">
<div className="text-gray-800 max-w-md">
    <div className="flex items-center gap-2 mb-2">
    <div className="w-8 md:w-11 h-[2px] bg-gray-800"></div>
    <p className="font-medium text-sm md:text-base uppercase tracking-wider text-gray-700">
        Our Bestsellers
    </p>
    </div>

    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-4">
    Latest Arrivals
    </h1>

    <div className="flex items-center gap-3 cursor-pointer group">
    <p className="font-semibold text-sm md:text-base text-gray-700 group-hover:text-black group-hover:underline transition">
        Shop Now
    </p>
    <div className="w-8 md:w-10 h-[1px] bg-gray-500 group-hover:w-12 transition-all duration-300"></div>
    </div>
</div>
</div>

{/* Hero Right Side */}
<div className="w-full sm:w-1/2">
<img
    className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
    src={assets.hero_img}
    alt="Hero"
/>
</div>
</div>
);
};

export default Hero;
