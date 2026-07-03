import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

// Set base URL for API requests
axios.defaults.baseURL = 'http://localhost:4000';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState({ _id: 'dummy-id', name: 'Student', email: 'student@example.com' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = async () => ({ success: true });
  const signup = async () => ({ success: true });
  const logout = () => {};
  const googleLogin = async () => ({ success: true });
  const githubLogin = async () => ({ success: true });

  return (
    <AuthContext.Provider 
      value={{ 
        user, 
        loading, 
        error, 
        login, 
        signup, 
        logout, 
        googleLogin, 
        githubLogin 
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
