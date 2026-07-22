"use client";

import { Languages, Moon, Sun } from 'lucide-react';
import { useAppContext } from '@/context/AppContext';

export function ThemeControls() {
  const { theme, toggleTheme, language, toggleLanguage } = useAppContext();
  const controlClass = "rounded-full border border-[#b98332]/30 bg-[#fff9e8]/70 p-2.5 text-[#123c69] transition hover:border-[#d6a63a] hover:bg-[#f3d77b]/25 dark:bg-[#0b2840]/80 dark:text-[#f3d77b]";
  return (
    <div className="flex items-center gap-2">
      <button onClick={toggleLanguage} className={`${controlClass} flex items-center gap-1.5 px-3 text-sm font-semibold`} aria-label="Change language">
        <Languages className="h-4 w-4" /> {language === 'en' ? 'عربي' : 'EN'}
      </button>
      <button onClick={toggleTheme} className={controlClass} aria-label="Change color theme">
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </div>
  );
}
