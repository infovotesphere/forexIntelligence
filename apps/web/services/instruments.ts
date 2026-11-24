export const instrumentGroups = [
  {
    label: "Forex majors",
    symbols: ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"],
  },
  {
    label: "Forex crosses",
    symbols: [
      "EURGBP", "EURJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
      "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
      "AUDJPY", "AUDCAD", "AUDNZD", "AUDCHF",
      "CADJPY", "CADCHF", "CHFJPY",
      "NZDJPY", "NZDCAD", "NZDCHF",
    ],
  },
  {
    label: "Metals",
    symbols: ["XAUUSD"],
  },
  {
    label: "Crypto",
    symbols: ["BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "LTCUSD", "BCHUSD", "AVAXUSD"],
  },
] as const;

export const searchableInstrumentGroups = instrumentGroups.map(({ label, symbols }) => ({
  label,
  options: symbols.map((symbol) => ({ value: symbol, label: symbol })),
}));
