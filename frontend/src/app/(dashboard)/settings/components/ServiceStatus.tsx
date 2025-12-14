'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react'
import apiClient from '@/lib/api/client'

interface ServiceHealth {
  name: string
  status: 'healthy' | 'unhealthy' | 'checking'
  url?: string
  error?: string
}

interface ServicesHealthResponse {
  services: ServiceHealth[]
  timestamp: string
}

async function checkServicesHealth(): Promise<ServicesHealthResponse> {
  const response = await apiClient.get<ServicesHealthResponse>('/health/services')
  return response.data
}

export function ServiceStatus() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['services-health'],
    queryFn: checkServicesHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const getStatusIcon = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-destructive" />
      case 'checking':
        return <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
    }
  }

  const getStatusBadge = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy':
        return <Badge variant="default" className="bg-green-500">Healthy</Badge>
      case 'unhealthy':
        return <Badge variant="destructive">Unhealthy</Badge>
      case 'checking':
        return <Badge variant="secondary">Checking...</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Service Status</CardTitle>
            <CardDescription>
              Monitor the health of external services
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && !data ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4">
            {data?.services.map((service) => (
              <div
                key={service.name}
                className="flex items-center justify-between p-4 rounded-lg border"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(service.status)}
                  <div>
                    <div className="font-medium">{service.name}</div>
                    {service.url && (
                      <div className="text-sm text-muted-foreground">
                        {service.url}
                      </div>
                    )}
                    {service.error && (
                      <div className="text-sm text-destructive mt-1">
                        {service.error}
                      </div>
                    )}
                  </div>
                </div>
                {getStatusBadge(service.status)}
              </div>
            ))}
            {data?.timestamp && (
              <div className="text-xs text-muted-foreground text-center pt-2">
                Last checked: {new Date(data.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
