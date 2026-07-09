export function truncateError(error: unknown, maxLength = 200): string {
  const message = String(error).replace(/\s+/g, " ").trim();
  if (message.length <= maxLength) {
    return message;
  }
  return `${message.slice(0, maxLength - 1)}…`;
}

export function isValidPort(value: number): boolean {
  return Number.isInteger(value) && value > 0 && value <= 65535;
}

export function isValidDataDir(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.length > 0 && trimmed.startsWith("/");
}
