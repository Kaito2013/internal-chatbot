import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Admin Panel - Internal Chatbot',
  description: 'Admin dashboard for managing internal chatbot',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-background antialiased">
        {children}
      </body>
    </html>
  );
}
