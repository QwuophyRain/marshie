// Write out what a recording says, using the listener on the Marshie computer (Vosk).
// The browser opens the file, turns it into 16 kHz mono sound, and sends it in short pieces.
import { api } from '../api'

const PIECE_SECONDS = 25            // the server accepts up to 30 seconds at a time

export async function transcribeFile(file, onProgress) {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx || !window.OfflineAudioContext) throw new Error('This browser cannot open recordings. Please type what it says instead.')
  const ctx = new Ctx()
  let audio
  try {
    audio = await ctx.decodeAudioData(await file.arrayBuffer())
  } catch {
    throw new Error('This browser could not open that recording. Please type what it says instead.')
  } finally {
    ctx.close().catch(() => {})
  }
  const off = new OfflineAudioContext(1, Math.max(1, Math.ceil(audio.duration * 16000)), 16000)
  const src = off.createBufferSource()
  src.buffer = audio
  src.connect(off.destination)
  src.start()
  const samples = (await off.startRendering()).getChannelData(0)

  const piece = 16000 * PIECE_SECONDS
  const parts = []
  for (let i = 0; i < samples.length; i += piece) {
    const slice = samples.subarray(i, Math.min(samples.length, i + piece))
    const pcm = new Int16Array(slice.length)
    for (let k = 0; k < slice.length; k++) {
      const v = Math.max(-1, Math.min(1, slice[k]))
      pcm[k] = v < 0 ? v * 0x8000 : v * 0x7fff
    }
    const text = await api.stt(pcm.buffer)
    if (text) parts.push(text.trim())
    onProgress?.(Math.min(1, (i + piece) / samples.length))
  }
  return parts.join(' ')
}
