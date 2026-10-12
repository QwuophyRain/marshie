// Make a big photo small enough to keep: scaled down and saved as a JPEG until it fits.
export async function fitImage(file, maxBytes) {
  if (!/^image\/(png|jpeg|webp)$/.test(file.type) || (file.size <= Math.min(maxBytes, 1.2 * 1024 * 1024))) return file
  let bitmap
  try { bitmap = await createImageBitmap(file) } catch { return file }
  for (const edge of [1600, 1280, 1000, 760, 560]) {
    const scale = Math.min(1, edge / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'                       // JPEG has no see-through parts
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    for (const quality of [0.86, 0.72, 0.58]) {
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
      if (blob && blob.size <= maxBytes) {
        return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' })
      }
    }
  }
  bitmap.close?.()
  return file
}
