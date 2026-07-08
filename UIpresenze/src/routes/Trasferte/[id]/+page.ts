import { redirect } from '@sveltejs/kit';

export const ssr = false;

export function load({ params }) {
  throw redirect(307, `/Trasferte/${params.id}`);
}
