const FAVORITE_AUTO_STORAGE_KEY = 'app-presenze:favorite-automobile-id';

export function getFavoriteAutomobileId(): string {
  if (typeof localStorage === 'undefined') return '';
  return localStorage.getItem(FAVORITE_AUTO_STORAGE_KEY) || '';
}

export function setFavoriteAutomobileId(autoId: number | string | null) {
  if (typeof localStorage === 'undefined') return;
  if (autoId === null || autoId === undefined || String(autoId) === '') {
    localStorage.removeItem(FAVORITE_AUTO_STORAGE_KEY);
    return;
  }
  localStorage.setItem(FAVORITE_AUTO_STORAGE_KEY, String(autoId));
}

export function isFavoriteAutomobile(autoId: number | string | null, favoriteAutoId: string): boolean {
  return autoId !== null && String(autoId) === String(favoriteAutoId || '');
}

export function sortFavoriteAutomobileFirst<T>(
  list: T[],
  favoriteAutoId: string,
  getAutoId: (item: T) => number | string | null
): T[] {
  if (!favoriteAutoId) return list;
  return [...list].sort((a, b) => {
    const aFavorite = isFavoriteAutomobile(getAutoId(a), favoriteAutoId);
    const bFavorite = isFavoriteAutomobile(getAutoId(b), favoriteAutoId);
    if (aFavorite === bFavorite) return 0;
    return aFavorite ? -1 : 1;
  });
}
