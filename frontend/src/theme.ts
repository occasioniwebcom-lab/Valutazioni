// Design tokens for GameLife Valutazioni — "iOS-Native Clean" personality.
export const colors = {
  surface: "#FCFDFC",
  onSurface: "#181C1A",
  surfaceSecondary: "#FFFFFF",
  surfaceTertiary: "#F1F4F2",
  onSurfaceTertiary: "#3E4C45",
  surfaceInverse: "#181C1A",
  onSurfaceInverse: "#FFFFFF",
  brand: "#2A5A43",
  brandPrimary: "#1F4734",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#C9E2D4",
  onBrandSecondary: "#1F4734",
  brandTertiary: "#E3EFE8",
  onBrandTertiary: "#1A3B2B",
  success: "#2A5A43",
  warning: "#B87503",
  error: "#9E2A2B",
  onError: "#FFFFFF",
  muted: "#7A8A82",
  border: "#E6EBE8",
  borderStrong: "#B0C4B9",
  divider: "#E6EBE8",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  "2xl": 32,
  "3xl": 48,
} as const;

export const radius = {
  sm: 6,
  md: 12,
  lg: 20,
  pill: 999,
} as const;

export const font = {
  regular: "Geist",
  medium: "Geist-Medium",
  semibold: "Geist-SemiBold",
  bold: "Geist-Bold",
  mono: "GeistMono",
  monoMedium: "GeistMono-Medium",
  monoSemibold: "GeistMono-SemiBold",
} as const;

export const fontSize = {
  sm: 12,
  base: 14,
  lg: 16,
  xl: 20,
  "2xl": 24,
} as const;

export const shadow = {
  card: {
    shadowColor: "#0B140F",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  raised: {
    shadowColor: "#0B140F",
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 8,
  },
} as const;

export const SHOP_LOGO = "https://www.videogamesitalia.it/img/1761001592.webp";
export const SHOP_NAME = "VideogamesItalia";
