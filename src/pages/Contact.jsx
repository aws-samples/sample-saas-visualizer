import React from 'react'
import Title from '../components/Title'
import { assets } from '../assets/assets'

const Contact = () => {
  return (
    <div>

      <div className='text-center text-2xl pt-10 border-t'>
        <Title text1={'CONTACT'} text2={'US'} />
      </div>

      <div className='my-10 flex flex-col justify-center md:flex-row gap-10 mb-28'>
        <img className='w-full md:max-w-[480px]' src={assets.contact_img} alt="" />
        <div className='flex flex-col justify-center items-start gap-6'>
          <p className=' font-semibold text-xl text-gray-600'>About This Demo</p>
          <p className=' text-gray-500'>This is a demonstration application showcasing multi-tenant SaaS architecture patterns on AWS.</p>
          <p className=' text-gray-500'>For more information about implementing similar solutions, please consult the documentation.</p>
          <p className=' font-semibold text-xl text-gray-600'>Learn More</p>
          <p className=' text-gray-500'>Explore AWS SaaS best practices and reference architectures.</p>
          <button className='border border-black px-8 py-4 text-sm hover:bg-black hover:text-white transition-all duration-500'>View Documentation</button>
        </div>
      </div>

    </div>
  )
}

export default Contact
