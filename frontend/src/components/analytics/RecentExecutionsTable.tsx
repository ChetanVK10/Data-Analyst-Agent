import React from 'react';
import type { HistoricalReport } from '../../types/index';
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';

interface RecentExecutionsTableProps {
  sessionQueries: HistoricalReport[];
  sessionId?: string;
}

export const RecentExecutionsTable: React.FC<RecentExecutionsTableProps> = ({ sessionQueries, sessionId }) => {
  if (sessionQueries.length === 0) {
    return null;
  }

  return (
    <Card className="border-border bg-card mt-6">
      <CardHeader>
        <CardTitle>Recent Execution Performance Logs</CardTitle>
        <CardDescription>
          {sessionId ? `Running under session ID: ${sessionId}` : 'Baseline query operations log'}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Execution ID</TableHead>
                <TableHead>Analysis Question</TableHead>
                <TableHead className="text-center">Pipeline Status</TableHead>
                <TableHead className="text-right">Latency</TableHead>
                <TableHead className="text-right">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessionQueries.map(exec => (
                <TableRow key={exec.id}>
                  <TableCell className="font-mono text-primary text-xs">#{exec.id}</TableCell>
                  <TableCell className="max-w-[280px] truncate font-medium text-xs" title={exec.question}>
                    {exec.question}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={exec.success ? 'default' : 'destructive'} className={exec.success ? 'bg-success/20 text-success hover:bg-success/30' : ''}>
                      {exec.success ? 'Succeeded' : 'Failed'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground text-xs">
                    {exec.execution_time_ms < 1000 ? `${exec.execution_time_ms}ms` : `${(exec.execution_time_ms / 1000).toFixed(1)}s`}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground text-xs">
                    {new Date(exec.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};
