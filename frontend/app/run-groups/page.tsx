"use client";

import { useState } from 'react';
import useSWR from 'swr';
import api from '@/app/hooks/useApi';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

type RunGroup = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
};

export default function RunGroupsPage() {
  const { data: groups, isLoading, mutate } = useSWR<RunGroup[]>('runs/groups', (url: string) => 
    api.get(url).then((r) => r.data)
  );
  
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsCreating(true);

    try {
      await api.post('runs/groups', { name, description });
      setName('');
      setDescription('');
      setShowForm(false);
      mutate(); // Refresh the list
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create run group');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Run Groups</h1>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'New Run Group'}
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-muted/50 p-4 rounded-lg space-y-4">
          <div>
            <Label htmlFor="group-name">Group Name</Label>
            <Input
              id="group-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Sacramento Flood Study"
              required
              className="mt-1"
            />
          </div>
          
          <div>
            <Label htmlFor="group-description">Description</Label>
            <Textarea
              id="group-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the scenarios being compared..."
              className="mt-1"
              rows={3}
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <Button type="submit" disabled={isCreating}>
            {isCreating ? 'Creating...' : 'Create Group'}
          </Button>
        </form>
      )}

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <div className="space-y-4">
          {groups?.length === 0 ? (
            <p className="text-muted-foreground">No run groups yet. Create one to start comparing scenarios.</p>
          ) : (
            groups?.map((group) => (
              <div key={group.id} className="border rounded-lg p-4 hover:bg-muted/20">
                <h3 className="font-semibold">
                  <Link href={`/run-groups/${group.id}`} className="text-blue-600 hover:underline">
                    {group.name}
                  </Link>
                </h3>
                {group.description && (
                  <p className="text-sm text-muted-foreground mt-1">{group.description}</p>
                )}
                <p className="text-xs text-muted-foreground mt-2">
                  Created: {new Date(group.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
} 