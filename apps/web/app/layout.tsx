import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import { ToastProvider } from '@/components/Toast'
import './globals.css'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' })

export const metadata: Metadata = {
  title: 'AtlasOS — Market Intelligence',
  description:
    'Map the competitive landscape of any B2B company. Structured market maps, competitive analysis, and strategic memos in under 60 seconds.',
  openGraph: {
    title: 'AtlasOS — Market Intelligence',
    description: 'Competitive cartography for B2B companies.',
    siteName: 'AtlasOS',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-black text-white antialiased">
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  )
}
