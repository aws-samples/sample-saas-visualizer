import React, { createContext, useState, useEffect, useContext } from 'react';
import { fetchTenants } from '../services/tenantService';

// Context for tenant selection and management
const TenantContext = createContext();

export const TenantProvider = ({ children }) => {
  const [tenants, setTenants] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch tenants on component mount
  useEffect(() => {
    const getTenants = async () => {
      try {
        setLoading(true);
        const tenantsData = await fetchTenants();
        
        if (tenantsData && tenantsData.length > 0) {
          setTenants(tenantsData);
          setSelectedTenant(tenantsData[0]); // Select first tenant by default
        } else {
          // Fallback to a default tenant if no tenants are returned
          const defaultTenant = { id: 'default', name: 'Default Tenant', tenantColor: '#3B82F6' };
          setTenants([defaultTenant]);
          setSelectedTenant(defaultTenant);
        }
      } catch (err) {
        console.error('Error fetching tenants:', err);
        setError('Failed to load tenants. Using default tenant.');
        
        // Fallback to a default tenant on error
        const defaultTenant = { id: 'default', name: 'Default Tenant', tenantColor: '#3B82F6' };
        setTenants([defaultTenant]);
        setSelectedTenant(defaultTenant);
      } finally {
        setLoading(false);
      }
    };
    
    getTenants();
  }, []);

  const addTenant = (newTenant) => {
    setTenants(prev => [...prev, newTenant]);
  };

  return (
    <TenantContext.Provider value={{ 
      tenants,
      selectedTenant,
      setSelectedTenant,
      addTenant,
      loading,
      error
    }}>
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = () => useContext(TenantContext);
