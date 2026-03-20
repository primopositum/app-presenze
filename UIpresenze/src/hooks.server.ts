import type { Handle } from '@sveltejs/kit';

// Bearer-only frontend: nessuna auth lato server necessaria
export const handle: Handle = async ({ event, resolve }) => {
  return resolve(event);
};
