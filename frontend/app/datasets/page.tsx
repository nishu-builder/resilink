import { redirect } from 'next/navigation';

export default function DatasetsIndex() {
  redirect('/datasets/hazards');
  return null;
} 