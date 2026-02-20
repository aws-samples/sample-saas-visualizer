import { fetchAuthSession } from "aws-amplify/auth";

// Use runtime configuration for Mystery Box API URL
const NEW_USER_STAGE_API_URL = window.APP_CONFIG.api.newUserStageUrl;

const getAuthToken = async () => {
    const session = await fetchAuthSession();
    console.log("id token", session.tokens.idToken);
    console.log("access token", session.tokens.accessToken);
    return session.tokens.idToken;
};

// NOT IMPLEMENTED: Tenant CRUD operations removed
export const fetchTenants = async () => {
    throw new Error("Tenant data operations not implemented - Amplify data resource removed");
};

// NOT IMPLEMENTED: Tenant CRUD operations removed
export const createTenant = async ({ email, tenantName, tenantColor }) => {
    throw new Error("Tenant creation not implemented - Amplify data resource removed");
};

export const handleCreateSampleOrder = async (tenantId) => {
    try {
        console.log("Creating sample order for tenant:", Number(tenantId));
        const token = await getAuthToken(); // Get Cognito token

        const response = await fetch(NEW_USER_STAGE_API_URL, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`, // Add Authorization header
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to create sample order: ${errorText}`);
        }

        const result = await response.json();
        console.log("Sample Order Created:", result);
        return result;
    } catch (error) {
        console.error("Error creating sample order:", error);
        throw error;
    }
};
