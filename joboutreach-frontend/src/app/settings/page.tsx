'use client'

import { useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { CheckCircle2, AlertCircle } from 'lucide-react'

function SettingsCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const gmailStatus = searchParams.get('gmail')
    const reason = searchParams.get('reason')

    if (gmailStatus === 'connected') {
      toast.success('Gmail account connected successfully!')
      setTimeout(() => router.push('/'), 1500)
    } else if (gmailStatus === 'error') {
      toast.error(`Gmail connection failed (${reason || 'Unknown error'})`)
      setTimeout(() => router.push('/'), 2000)
    } else {
      router.push('/')
    }
  }, [searchParams, router])

  return (
    <div className="app-shell min-h-screen flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="section-card p-8 sm:p-10 rounded-[1.75rem] max-w-md w-full text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
          <CheckCircle2 size={24} />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Processing Gmail OAuth...</h2>
        <p className="text-sm text-slate-600">Redirecting you back to your job search dashboard...</p>
      </div>
    </div>
  )
}

export default function SettingsCallbackPage() {
  return (
    <Suspense>
      <SettingsCallbackContent />
    </Suspense>
  )
}
