import { create } from 'zustand';

interface AppState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  setDarkMode: (enabled: boolean) => void;
  activeReportTab: string;
  setActiveReportTab: (tab: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  isDarkMode: true,
  toggleDarkMode: () =>
    set((state) => {
      const next = !state.isDarkMode;
      if (next) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
      return { isDarkMode: next };
    }),
  setDarkMode: (enabled: boolean) => {
    if (enabled) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    set({ isDarkMode: enabled });
  },
  activeReportTab: 'overview',
  setActiveReportTab: (tab: string) => set({ activeReportTab: tab }),
}));
