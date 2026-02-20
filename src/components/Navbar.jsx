import React, { useContext, useState, useEffect } from 'react';
import { assets } from '../assets/assets';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { ShopContext } from '../context/ShopContext';
import { fetchAuthSession, signOut, signIn } from '@aws-amplify/auth';
import MysteryBox from './MysteryBox';

// Helper function to construct email from tenant ID based on current user's email pattern
const getEmailForTenant = (tenantId, currentUserEmail) => {
  if (!currentUserEmail) {
    return `user-${tenantId}@example.com`;
  }
  
  // Extract pattern from current user's email (e.g., "smusand+1@amazon.com" -> "smusand+" and "@amazon.com")
  const match = currentUserEmail.match(/^(.+?)(\d+)(@.+)$/);
  if (match) {
    const [, prefix, , suffix] = match;
    return `${prefix}${tenantId}${suffix}`;
  }
  
  // Fallback if pattern doesn't match
  return `user-${tenantId}@example.com`;
};


const Navbar = ({ user, setShowLogin }) => {
  const [visible, setVisble] = useState(false);
  const [isSwitchModalOpen, setIsSwitchModalOpen] = useState(false);
  const [selectedUserKey, setSelectedUserKey] = useState("");
  const [passwordForSwitch, setPasswordForSwitch] = useState("");
  const [switchMessage, setSwitchMessage] = useState({ type: "", text: "" });
  const [fadeOut, setFadeOut] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { setShowSearch, getCartCount } = useContext(ShopContext);
  const navigate = useNavigate();
  const tenantColor = user?.["custom:tenantColor"] || "#ff0000";

  // Get current user's email to extract pattern
  const currentUserEmail = user?.email || "";

  // Create user mapping dictionary with actual emails (dynamically when component renders)
  const userMapping = {};
  for (let i = 1; i <= 24; i++) {
    userMapping[`user-${i}`] = getEmailForTenant(i, currentUserEmail);
  }

  const handleSignOut = async () => {
    try {
      await signOut();
      if (typeof window !== "undefined" && window.dispatchEvent) {
        window.dispatchEvent(new Event("logout"));
      }
      navigate('/');
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  const handleSwitchUser = async () => {
    if (!selectedUserKey || !passwordForSwitch) {
      setSwitchMessage({ type: "error", text: "Please select a user and enter password." });
      return;
    }

    const actualUsername = userMapping[selectedUserKey];
    if (!actualUsername) {
      setSwitchMessage({ type: "error", text: "Invalid user selected." });
      return;
    }

    try {
      await signOut();
      await signIn({ username: actualUsername, password: passwordForSwitch });
      const session = await fetchAuthSession();
      const loginSuccessEvent = new CustomEvent("loginSuccess", { detail: session.tokens?.idToken?.payload });
      window.dispatchEvent(loginSuccessEvent);
      setSwitchMessage({ type: "success", text: `Switched to ${actualUsername} successfully!` });

      setTimeout(() => setFadeOut(true), 500);
      setTimeout(() => window.location.reload(), 1200);
    } catch (error) {
      console.error("Switch user error:", error);
      setSwitchMessage({ type: "error", text: "Failed to switch user. Please try again." });
    }
  };

  // ESC key closes modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isSwitchModalOpen) {
        setIsSwitchModalOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isSwitchModalOpen]);

  return (
    <>
      {/* Navbar */}
      <div className="flex items-center justify-between py-5 px-4 sm:px-10 font-medium bg-white/90 backdrop-blur-md shadow-md rounded-b-xl transition-all duration-300 z-50">
        <Link to="/" className="text-2xl font-bold text-blue-600">
          SaaS Visualiser
        </Link>

        <ul className="hidden sm:flex gap-6 text-sm sm:text-base text-gray-700 tracking-wide">
          {['/', '/collection', '/about', '/contact'].map((path, i) => {
            const labels = ['Home', 'Collection', 'About', 'Contact'];
            return (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 transition duration-300 hover:text-blue-600 ${
                    isActive ? 'text-blue-600 font-semibold border-b-2 border-blue-600 pb-1' : ''
                  }`
                }
              >
                <p className="uppercase">{labels[i]}</p>
              </NavLink>
            );
          })}
        </ul>

        <div className="flex items-center gap-6">
          <img
            onClick={() => {
              setShowSearch(true);
              navigate('/collection');
            }}
            className="w-5 cursor-pointer"
            src={assets.search_icon}
            alt="Search"
          />
          <MysteryBox compact tenantId={user?.['custom:tenantName']} />

          {/* Profile dropdown */}
          <div className="group relative">
            <div className="flex items-center gap-2">
              <img className="w-5 cursor-pointer" src={assets.profile_icon} alt="Profile" />
              {user && (
                <span className="text-sm text-white px-2 py-1 rounded" style={{ backgroundColor: tenantColor }}>
                  Tenant- {user?.['custom:tenantName']}
                </span>
              )}
            </div>

            <div className="group-hover:block hidden absolute dropdown-menu right-0 pt-4">
              <div className="flex flex-col gap-2 w-44 py-3 px-5 bg-white border rounded-lg shadow-lg text-gray-600">
                {user ? (
                  <>
                    <p className="text-black font-semibold">Hello, {user?.['custom:tenantName']} </p>
                    <p onClick={() => {}} className="cursor-pointer hover:text-black">My Profile</p>
                    <p onClick={() => navigate('/orders')} className="cursor-pointer hover:text-black">Orders</p>
                    <hr className="border-t border-gray-300 my-2" />
                    <p
                      onClick={() => {
                        setSwitchMessage({ type: "", text: "" });
                        setFadeOut(false);
                        setSelectedUserKey("");
                        setPasswordForSwitch("");
                        setIsSwitchModalOpen(true);
                      }}
                      className="cursor-pointer hover:text-black text-blue-600 font-semibold"
                    >
                      Switch User
                    </p>
                    <p
                      onClick={handleSignOut}
                      className="cursor-pointer hover:text-black text-red-500 font-semibold"
                    >
                      Sign Out
                    </p>
                  </>
                ) : (
                  <p onClick={() => { setShowLogin(true); navigate('/'); }} className="cursor-pointer hover:text-black">Login</p>
                )}
              </div>
            </div>
          </div>

          <Link to="/cart" className="relative">
            <img className="w-5 min-w-5" src={assets.cart_icon} alt="Cart" />
            <p className="absolute right-[-5px] bottom-[-5px] w-4 text-center leading-4 bg-black text-white aspect-square rounded-full text-[8px]">
              {getCartCount()}
            </p>
          </Link>

          <img
            onClick={() => setVisble(true)}
            className="w-5 cursor-pointer sm:hidden"
            src={assets.menu_icon}
            alt="Menu"
          />
        </div>
      </div>

      {/* Switch User Modal */}
      {isSwitchModalOpen && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <div className="bg-white p-8 rounded-lg w-80 flex flex-col gap-4 shadow-lg transform transition-all duration-500 scale-100 opacity-100 translate-y-0">
            <h2 className="text-xl font-bold text-center mb-2">Switch User</h2>

            {/* Only single select dropdown */}
            <select
              value={selectedUserKey}
              onChange={(e) => setSelectedUserKey(e.target.value)}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="">Select User</option>
              {Object.keys(userMapping).map((key) => (
                <option key={key} value={key}>
                  {userMapping[key]}
                </option>
              ))}
            </select>

            {/* Password field */}
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter password"
                value={passwordForSwitch}
                onChange={(e) => setPasswordForSwitch(e.target.value)}
                className="border rounded px-3 py-2 text-sm w-full pr-10"
              />
              <span
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute top-1/2 right-3 transform -translate-y-1/2 text-gray-600 cursor-pointer text-lg"
              >
                {showPassword ? '🙈' : '👁️'}
              </span>
            </div>

            {/* Buttons */}
            <div className="flex gap-4 justify-center mt-2">
              <button
                onClick={handleSwitchUser}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded px-4 py-2 text-sm"
              >
                Switch
              </button>
              <button
                onClick={() => setIsSwitchModalOpen(false)}
                className="border border-gray-400 text-gray-600 rounded px-4 py-2 text-sm"
              >
                Cancel
              </button>
            </div>

            {/* Inline message */}
            {switchMessage.text && (
              <p className={`text-center text-sm mt-2 transition-opacity duration-500 ${fadeOut ? 'opacity-0' : 'opacity-100'} ${switchMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {switchMessage.text}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default Navbar;
