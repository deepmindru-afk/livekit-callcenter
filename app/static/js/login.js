// Login form handling
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');

    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
        // Redirect to main page if already logged in
        window.location.href = '/';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Reset error message
        loginError.textContent = '';
        
        try {
            // Fixed endpoint from /api/auth/login to /api/login
            // The FastAPI OAuth2 form requires form URL encoded data, not JSON
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Login failed. Please check your credentials.');
            }
            
            // Store authentication token in localStorage
            localStorage.setItem('token', data.access_token);
            
            // Get agent information using the token
            const agentResponse = await fetch('/api/agents/me', {
                headers: {
                    'Authorization': `Bearer ${data.access_token}`
                }
            });
            
            if (!agentResponse.ok) {
                throw new Error('Failed to get agent information');
            }
            
            const agentData = await agentResponse.json();
            
            // Log agent status for debugging
            console.log('Agent status after login:', agentData.status);
            
            // Double-check that agent status is Available - if not, force update
            if (agentData.status !== 'Available') {
                console.log('Agent status not Available after login, forcing update...');
                try {
                    const statusUpdateResponse = await fetch('/api/agents/status', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${data.access_token}`
                        },
                        body: JSON.stringify({ status: 'Available' })
                    });
                    
                    if (statusUpdateResponse.ok) {
                        console.log('Successfully forced agent status to Available');
                    } else {
                        console.error('Failed to force agent status to Available');
                    }
                } catch (statusError) {
                    console.error('Error updating agent status:', statusError);
                }
            }
            
            // Store agent info
            localStorage.setItem('agent', JSON.stringify({
                id: agentData.id,
                name: agentData.full_name || agentData.username
            }));
            
            // Redirect to the main agent interface page
            window.location.href = '/';
            
        } catch (error) {
            loginError.textContent = error.message;
            console.error('Login error:', error);
        }
    });
}); 