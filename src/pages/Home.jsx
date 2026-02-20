import React from 'react';
import Hero from '../components/Hero';
import LatestCollection from '../components/LatestCollection';
import BestSeller from '../components/BestSeller';
import OurPolicy from '../components/OurPolicy';
import MysteryBox from '../components/MysteryBox'; 

const Home = () => {
  return (
    <div className="bg-gray-50">
    
      <Hero />
      <LatestCollection />
      <BestSeller />
      <OurPolicy />
      <MysteryBox /> 
    </div>
  );
};

export default Home;
