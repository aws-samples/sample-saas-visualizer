import React, { useState, useEffect } from "react";
import { fetchAuthSession, signOut } from "@aws-amplify/auth";
import { Hub } from "aws-amplify/utils";
import { Route, Routes, Navigate, useLocation } from "react-router-dom";
import { Authenticator, useTheme,View, Image, Text} from "@aws-amplify/ui-react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "@aws-amplify/ui-react/styles.css";

import { Amplify } from "aws-amplify";
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: window.APP_CONFIG.auth.userPoolId,
      userPoolClientId: window.APP_CONFIG.auth.userPoolClientId,
      region: window.APP_CONFIG.auth.region,
    }
  }
});

// Components
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import SearchBar from "./components/SearchBar";

// Pages
import Home from "./pages/Home";
import Collection from "./pages/Collection";
import About from "./pages/About";
import Contact from "./pages/Contact";
import Cart from "./pages/Cart";
import Product from "./pages/Product";
import Orders from "./pages/Orders";
import PlaceOrder from "./pages/PlaceOrder";


const App = () => {
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const location = useLocation(); // Get the current route

  useEffect(() => {
    const checkUser = async () => {
      try {
        const session = await fetchAuthSession();
        setUser(session.tokens?.idToken?.payload);
      } catch {
        setUser(null);
      }
    };
    checkUser();

    const onLogout = () => {
      setUser(null);
      setShowLogin(false);
    };

    const onLoginSuccess = async () => {
      try {
        // Retry fetching session a few times in case it's not immediately available
        let session = null;
        let attempts = 0;
        const maxAttempts = 3;

        while (!session?.tokens?.idToken && attempts < maxAttempts) {
          try {
            session = await fetchAuthSession();
            if (session?.tokens?.idToken) break;
          } catch (e) {
            console.log(`Session fetch attempt ${attempts + 1} failed:`, e);
          }
          attempts++;
          if (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
        }

        if (session?.tokens?.idToken?.payload) {
          setUser(session.tokens.idToken.payload);
          setShowLogin(false);
        } else {
          console.error('Unable to fetch valid session after login');
        }
      } catch (error) {
        console.error('Error fetching session on loginSuccess:', error);
      }
    };

    // Listen directly to Amplify Hub events for authentication
    const hubListener = (data) => {
      const { payload } = data;
      console.log('Hub event received:', payload.event, payload.data);

      if (payload.event === 'signedIn') {
        console.log('User signed in via Hub event, fetching session...');
        onLoginSuccess();
      } else if (payload.event === 'signedOut') {
        console.log('User signed out via Hub event');
        onLogout();
      }
    };

    // Subscribe to Hub events
    const unsubscribe = Hub.listen('auth', hubListener);

    window.addEventListener("logout", onLogout);
    window.addEventListener("loginSuccess", onLoginSuccess);
    return () => {
      window.removeEventListener("logout", onLogout);
      window.removeEventListener("loginSuccess", onLoginSuccess);
      unsubscribe();
    };
  }, []);


  return (
    <div className="px-4 sm:px-[5vw] md:px-[7vw] lg:px-[9vw]">
      <ToastContainer />

      <Navbar user={user} setShowLogin={setShowLogin} />


      {/* Show login button if not logged in */}
      {!user && !showLogin && (
        <div className="min-h-[75vh] flex flex-col items-center justify-center text-center bg-gradient-to-br from-stone-100 via-white to-stone-200 rounded-lg shadow-md px-6 py-10 mt-10">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-blue-900 mb-6 tracking-tight">
            Welcome to SaaS Visualiser
          </h1>
          <p className="text-lg sm:text-xl text-gray-600 mb-8 max-w-xl">
            Discover, explore, and visualize SaaS usage like never before. <br /> Please log in to continue.
          </p>
          <button
            onClick={() => setShowLogin(true)}
            className="px-6 py-3 text-lg font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow transition-all duration-300"
          >
            Get Started
          </button>
        </div>
      )}

{showLogin && !user && (
  <div style={{ textAlign: "center", marginTop: "30px" }}>
    <Authenticator
      hideSignUp
      components={{
        Header: function () {
          const { tokens } = useTheme();
          return (
            <View textAlign="center" padding={tokens.space.large}>
              <Image
                alt="Amplify logo"
                src="https://docs.amplify.aws/assets/logo-dark.svg"
              />
            </View>
          );
        },
        Footer() {
          const { tokens } = useTheme();
          return (
            <View textAlign="center" padding={tokens.space.large}>
              <Text color={tokens.colors.neutral[80]}>
                &copy; SaaS Visualiser
              </Text>
            </View>
          );
        },
        SignIn: {
          Header() {
            return (
              <h1 className="text-2xl font-bold text-purple-600 mb-4">
                Welcome Back! Please Sign In
              </h1>
            );
          },
          Footer() {
            return null;
          },
        },
      }}
    >
      {({ signOut, user }) => {
        // Handle different authentication states
        if (user) {
          // Check if user has completed the full authentication flow
          if (user?.signInUserSession) {
            // User is fully authenticated - dispatch success event
            window.dispatchEvent(new Event("loginSuccess"));
          } else if (user?.challengeName) {
            // User is in a challenge state (e.g., MFA, password reset)
            // Let Authenticator handle the challenge
            return null;
          } else {
            // User exists but authentication might be complete even without signInUserSession
            // This handles cases where verification is skipped
            setTimeout(() => {
              window.dispatchEvent(new Event("loginSuccess"));
            }, 100);
          }
        }

        return null;
      }}
    </Authenticator>
  </div>
)}


      {/* If logged in, show full app layout */}
      {user && (
        <>
          <SearchBar />

          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/product/:productId" element={<Product />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/place-order" element={<PlaceOrder />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>

          <Footer />
        </>
      )}
    </div>
  );
};

export default App;
