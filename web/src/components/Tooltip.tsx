"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ReactNode, useState } from "react";

type ComingSoonTooltipProps = {
  text?: string;
  children: ReactNode;
  className?: string;
};

export function ComingSoonTooltip({
  text = "Feature coming soon in V2",
  children,
  className = ""
}: ComingSoonTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <span
      className={`relative inline-flex ${className}`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={() => setIsOpen(true)}
      onBlur={() => setIsOpen(false)}
    >
      {children}
      <AnimatePresence>
        {isOpen ? (
          <motion.span
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 w-max max-w-56 -translate-x-1/2 rounded-md border border-indigo-100 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-soft"
            role="tooltip"
          >
            {text}
          </motion.span>
        ) : null}
      </AnimatePresence>
    </span>
  );
}
