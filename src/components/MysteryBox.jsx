import React, { useState, useEffect } from 'react';
import { handleCreateSampleOrder } from '../services/tenantService';

const MysteryBox = ({ compact = false, tenantId }) => {
  const [showMysteryBox, setShowMysteryBox] = useState(true);
  const [status, setStatus] = useState(null); // null | 'loading' | 'success' | 'error'
  const [hovered, setHovered] = useState(false);

  // Auto-hide success/error message after 4 seconds
  useEffect(() => {
    if (status === 'success' || status === 'error') {
      const timer = setTimeout(() => {
        setStatus(null);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  const handleMysteryClick = async () => {
    if (!tenantId) return;
    setStatus('loading');
    try {
      await handleCreateSampleOrder(tenantId);
      setStatus('success');

      // ⏳ Wait 4 seconds before hiding box
      setTimeout(() => {
        setShowMysteryBox(false);
      }, 4000);
    } catch (err) {
      console.error("Mystery box error:", err);
      setStatus('error');

      // ❌ Hide error after 4 seconds too
      setTimeout(() => {
        setStatus(null);
      }, 4000);
    }
  };

  if (!tenantId) return null;

  const emojiSize = compact ? 'text-lg' : 'text-6xl';
  const emojiClass = `${emojiSize} animate-bounce hover:scale-125 transition-transform cursor-pointer`;

  return (
    <div
      className={`relative ${compact ? '' : 'flex flex-col items-center justify-center py-10'}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Box Click Action */}
      {status === 'loading' ? (
        <p className="text-sm animate-pulse text-blue-600 font-semibold">
          ⏳ Placing your mystery box...
        </p>
      ) : status === 'success' ? (
        <p className="text-green-600 font-semibold text-sm">
          🎉 Mystery Box opened! Sample orders placed!
        </p>
      ) : status === 'error' ? (
        <p className="text-red-600 font-semibold text-sm">
          ❌ Sorry, you've already consumed your Mystery Box!
        </p>
      ) : (
        showMysteryBox && (
          <span
            className={emojiClass}
            role="img"
            aria-label="mystery box"
            onClick={handleMysteryClick}
          >
            🎁
          </span>
        )
      )}

      {/* Hover Message */}
      {hovered && status === null && (
        <div className="absolute top-full mt-2 bg-white text-purple-700 text-xs font-medium px-3 py-1 rounded shadow-lg animate-fadeInUp">
          ✨ Order your mystery gift items!
        </div>
      )}
    </div>
  );
};

export default MysteryBox;
