import { create } from "zustand";

export type SwarmModalPreset = "weather" | "current-events" | null;

type UiState = {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  swarmModalOpen: boolean;
  swarmModalPreset: SwarmModalPreset;
  setSidebarOpen(v: boolean): void;
  setRightPanelOpen(v: boolean): void;
  openSwarmModal(preset?: SwarmModalPreset): void;
  closeSwarmModal(): void;
};

export const useUiStore = create<UiState>(set => ({
  sidebarOpen: true,
  rightPanelOpen: false,
  swarmModalOpen: false,
  swarmModalPreset: null,
  setSidebarOpen: v => set({ sidebarOpen: v }),
  setRightPanelOpen: v => set({ rightPanelOpen: v }),
  openSwarmModal: preset => set({ swarmModalOpen: true, swarmModalPreset: preset ?? null }),
  closeSwarmModal: () => set({ swarmModalOpen: false, swarmModalPreset: null }),
}));
