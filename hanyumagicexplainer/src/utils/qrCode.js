// src/utils/qrCode.js
import QRCode from 'qrcode'

export async function generateQRCode(url) {
  try {
    const qrSvg = await QRCode.toString(url, {
      type: 'svg',
      width: 100,
      margin: 2
    });
    return qrSvg;
  } catch (error) {
    console.error('Error generating QR code:', error);
    return '';
  }
}