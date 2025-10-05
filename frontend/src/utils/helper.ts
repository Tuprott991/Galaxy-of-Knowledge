export function randomClusterColor(
  clustersList: string[],
  colorsList: string[]
): Record<string, string> {
  const result: Record<string, string> = {};
  clustersList.forEach((clusterName) => {
    const color = colorsList[Math.floor(Math.random() * colorsList.length)];
    result[clusterName] = color;
  });
  return result;
}
