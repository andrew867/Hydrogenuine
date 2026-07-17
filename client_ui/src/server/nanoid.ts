export function nanoid(size = 14): string {
  const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
  let id = "";
  for (let i = 0; i < size; i++) id += alphabet[Math.floor(Math.random() * alphabet.length)];
  return id;
}
