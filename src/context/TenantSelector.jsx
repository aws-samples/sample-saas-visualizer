import React from 'react';
import { useTenant } from './TenantContext';
import { FormControl, InputLabel, Select, MenuItem } from '@mui/material';

const TenantSelector = () => {
  const { tenants, selectedTenant, setSelectedTenant } = useTenant();

  return (
    <FormControl fullWidth margin="normal">
      <InputLabel>Select Tenant</InputLabel>
      <Select 
        value={selectedTenant.tenantId} 
        onChange={(e) => {
          const tenant = tenants.find(t => t.tenantId === e.target.value);
          setSelectedTenant(tenant);
        }}
      >
        {tenants.map(tenant => (
          <MenuItem key={tenant.tenantId} value={tenant.tenantId}>
            {tenant.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default TenantSelector;
