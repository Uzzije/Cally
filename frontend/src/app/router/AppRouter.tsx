import { Route, Routes } from 'react-router-dom'

import { ErrorScreen } from '../components/ErrorScreen'
import { LoadingScreen } from '../components/LoadingScreen'
import { useAppShellState } from '../hooks/useAppShellState'
import { AuthErrorPage } from '../../features/auth/components/AuthErrorPage'
import { LoginPage } from '../../features/auth/components/LoginPage'
import { AnalyticsWorkspace } from '../../features/analytics/components/AnalyticsWorkspace'
import { CalendarWorkspace } from '../../features/calendar/components/CalendarWorkspace'
import { SettingsWorkspace } from '../../features/settings/components/SettingsWorkspace'
import { TempBlockedTimesWorkspace } from '../../features/settings/components/TempBlockedTimesWorkspace'


export function AppRouter() {
  const {
    addTempBlockedTimes,
    clearAllTempBlockedTimes,
    hasError,
    isLoading,
    loadSession,
    messageCredits,
    refreshMessageCredits,
    removeTempBlockedTime,
    session,
    tempBlockedTimes,
  } = useAppShellState()

  if (isLoading) {
    return <LoadingScreen />
  }

  if (hasError) {
    return (
      <ErrorScreen
        title="The backend session could not be loaded"
        message="Check that the Django backend is running and try again."
        onRetry={() => {
          void loadSession()
        }}
      />
    )
  }

  return (
    <Routes>
      <Route path="/auth/error" element={<AuthErrorPage />} />
      <Route
        path="/"
        element={
          session?.authenticated ? (
            <CalendarWorkspace
              messageCredits={messageCredits}
              onAddTempBlockedTimes={addTempBlockedTimes}
              onRefreshMessageCredits={refreshMessageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimes={tempBlockedTimes}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/analytics"
        element={
          session?.authenticated ? (
            <AnalyticsWorkspace
              messageCredits={messageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimesCount={tempBlockedTimes.length}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/settings"
        element={
          session?.authenticated ? (
            <SettingsWorkspace
              messageCredits={messageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimesCount={tempBlockedTimes.length}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/temp-blocked-times"
        element={
          session?.authenticated ? (
            <TempBlockedTimesWorkspace
              entries={tempBlockedTimes}
              messageCredits={messageCredits}
              onClearAll={clearAllTempBlockedTimes}
              onRefreshSession={loadSession}
              onRemove={removeTempBlockedTime}
              session={session}
            />
          ) : (
            <LoginPage />
          )
        }
      />
    </Routes>
  )
}
