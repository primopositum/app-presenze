import { writable } from 'svelte/store';
import {
  jiraTimesheet,
  jiraTimesheetMonth,
  type JiraTimesheetActivity,
  type JiraTimesheetMonthResponse,
  type JiraTimesheetParams,
  type JiraTimesheetResponse,
} from '$lib/services/jira';

type LoadMonthInput = {
  year: number;
  month: number;
  email?: string | null;
  force?: boolean;
};

type RefreshDayOptions = {
  silent?: boolean;
};

const monthCache = new Map<string, JiraTimesheetMonthResponse>();

function normalizeEmail(email?: string | null) {
  return String(email || '').trim().toLowerCase();
}

function cacheKey(year: number, month: number, email?: string | null) {
  return `${year}-${String(month).padStart(2, '0')}|${normalizeEmail(email)}`;
}

function paramsForEmail(email?: string | null): JiraTimesheetParams {
  const normalized = String(email || '').trim();
  return normalized ? { email: normalized } : {};
}

function cloneMonthPayload(payload: JiraTimesheetMonthResponse): JiraTimesheetMonthResponse {
  return {
    ...payload,
    users: [...(payload.users || [])],
    days: { ...(payload.days || {}) },
  };
}

function userKeyForDay(payload: JiraTimesheetMonthResponse | null, email?: string | null) {
  const normalized = normalizeEmail(email);
  if (normalized) {
    const matchedUser = (payload?.users || []).find(
      (user) =>
        normalizeEmail(user.utente_email) === normalized ||
        normalizeEmail(user.jira_email) === normalized
    );
    return matchedUser?.utente_email || matchedUser?.jira_email || String(email || '').trim();
  }

  const firstUser = payload?.users?.[0];
  return firstUser?.utente_email || firstUser?.jira_email || '';
}

function mergeDailyIntoMonth(
  current: JiraTimesheetMonthResponse,
  day: string,
  email: string,
  daily: JiraTimesheetResponse
) {
  const next = cloneMonthPayload(current);
  const userKey = userKeyForDay(next, email) || daily.utente_email || daily.jira_email || email;
  const existingDay = next.days?.[day] || { date: day, count: 0, users: {} };
  const previousUserCount = existingDay.users?.[userKey]?.count || 0;
  const nextUserCount = daily.activities?.length || 0;

  next.days = {
    ...next.days,
    [day]: {
      ...existingDay,
      count: Math.max(0, (existingDay.count || 0) - previousUserCount + nextUserCount),
      users: {
        ...(existingDay.users || {}),
        [userKey]: {
          utente_email: daily.utente_email,
          jira_email: daily.jira_email,
          count: nextUserCount,
          activities: daily.activities || [],
        },
      },
    },
  };
  next.count = Math.max(0, (next.count || 0) - previousUserCount + nextUserCount);

  let matchedUser = false;
  next.users = (next.users || []).map((user) => {
    const matches =
      normalizeEmail(user.utente_email) === normalizeEmail(userKey) ||
      normalizeEmail(user.jira_email) === normalizeEmail(userKey);
    if (!matches) return user;
    matchedUser = true;
    return {
      ...user,
      count: Math.max(0, (user.count || 0) - previousUserCount + nextUserCount),
      days: {
        ...(user.days || {}),
        [day]: {
          date: day,
          count: nextUserCount,
          activities: daily.activities || [],
        },
      },
    };
  });

  if (!matchedUser && userKey) {
    next.users = [
      ...next.users,
      {
        utente_email: daily.utente_email || userKey,
        jira_email: daily.jira_email,
        count: nextUserCount,
        days: {
          [day]: {
            date: day,
            count: nextUserCount,
            activities: daily.activities || [],
          },
        },
      },
    ];
    next.users_count = next.users.length;
  }

  return next;
}

export function getJiraActivitiesForDay(
  payload: JiraTimesheetMonthResponse | null,
  day: string | null,
  email?: string | null
): JiraTimesheetActivity[] {
  if (!payload || !day) return [];
  const dayPayload = payload.days?.[day];
  if (!dayPayload) return [];

  const userKey = userKeyForDay(payload, email);
  if (userKey && dayPayload.users?.[userKey]) {
    return dayPayload.users[userKey].activities || [];
  }

  const firstUserPayload = Object.values(dayPayload.users || {})[0];
  return firstUserPayload?.activities || [];
}

export function useJiraTimesheetMonthCache() {
  const data = writable<JiraTimesheetMonthResponse | null>(null);
  const loading = writable(false);
  const error = writable('');
  let activeKey = '';
  let activeYear = 0;
  let activeMonth = 0;
  let activeEmail = '';

  async function loadMonth(input: LoadMonthInput) {
    const year = Number(input.year);
    const month = Number(input.month);
    if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null;

    const email = String(input.email || '').trim();
    const key = cacheKey(year, month, email);
    activeKey = key;
    activeYear = year;
    activeMonth = month;
    activeEmail = email;

    if (!input.force && monthCache.has(key)) {
      const cached = monthCache.get(key) || null;
      data.set(cached);
      error.set('');
      return cached;
    }

    loading.set(true);
    error.set('');
    try {
      const payload = await jiraTimesheetMonth(year, month, paramsForEmail(email));
      monthCache.set(key, payload);
      if (activeKey === key) {
        data.set(payload);
      }
      return payload;
    } catch (e: any) {
      const message = String(e?.message || e || 'Errore caricamento worklog Jira');
      if (activeKey === key) {
        error.set(message);
      }
      throw e;
    } finally {
      if (activeKey === key) {
        loading.set(false);
      }
    }
  }

  function injectWorklogIntoCache(
    day: string,
    activity: JiraTimesheetActivity,
    emailOverride?: string | null
  ) {
    const email = String(emailOverride ?? activeEmail ?? '').trim();
    const key = cacheKey(activeYear, activeMonth, email);
    if (!day || !activeYear || !activeMonth) return false;

    const current = monthCache.get(key);
    if (!current) return false;

    const userKey = userKeyForDay(current, email) || email;
    const existingDay = current.days?.[day];
    const existingUser = existingDay?.users?.[userKey];
    const existingActivities = existingUser?.activities || [];
    const worklogId = String(activity.worklog_id || '').trim();
    const activities = [
      activity,
      ...existingActivities.filter(
        (item) => !worklogId || String(item.worklog_id || '').trim() !== worklogId
      ),
    ];
    const next = mergeDailyIntoMonth(current, day, email, {
      date: day,
      utente_email: existingUser?.utente_email || userKey || undefined,
      jira_email: existingUser?.jira_email || email || undefined,
      count: activities.length,
      activities,
    });

    monthCache.set(key, next);
    if (activeKey === key) {
      data.set(next);
    }
    return true;
  }

  function removeWorklogFromCache(
    day: string,
    worklogId: string | number,
    emailOverride?: string | null
  ) {
    const email = String(emailOverride ?? activeEmail ?? '').trim();
    const key = cacheKey(activeYear, activeMonth, email);
    const normalizedWorklogId = String(worklogId || '').trim();
    if (!day || !normalizedWorklogId || !activeYear || !activeMonth) return false;

    const current = monthCache.get(key);
    if (!current) return false;

    const userKey = userKeyForDay(current, email) || email;
    const existingDay = current.days?.[day];
    const existingUser = existingDay?.users?.[userKey];
    if (!existingUser) return false;

    const activities = (existingUser.activities || []).filter(
      (item) => String(item.worklog_id || '').trim() !== normalizedWorklogId
    );
    if (activities.length === (existingUser.activities || []).length) return false;

    const next = mergeDailyIntoMonth(current, day, email, {
      date: day,
      utente_email: existingUser.utente_email,
      jira_email: existingUser.jira_email,
      count: activities.length,
      activities,
    });

    monthCache.set(key, next);
    if (activeKey === key) {
      data.set(next);
    }
    return true;
  }

  async function refreshDay(
    day: string,
    emailOverride?: string | null,
    options: RefreshDayOptions = {}
  ) {
    const email = String(emailOverride ?? activeEmail ?? '').trim();
    const key = cacheKey(activeYear, activeMonth, email);
    if (!day || !activeYear || !activeMonth) return null;

    if (!options.silent) {
      loading.set(true);
      error.set('');
    }
    try {
      const daily = await jiraTimesheet(day, paramsForEmail(email));
      const current = monthCache.get(key);
      if (!current) {
        if (!options.silent) {
          await loadMonth({ year: activeYear, month: activeMonth, email, force: true });
        }
        return daily;
      }

      const next = mergeDailyIntoMonth(current, day, email, daily);

      monthCache.set(key, next);
      if (activeKey === key) {
        data.set(next);
      }
      return daily;
    } catch (e: any) {
      if (!options.silent && activeKey === key) {
        error.set(String(e?.message || e || 'Errore aggiornamento worklog Jira'));
      }
      throw e;
    } finally {
      if (!options.silent && activeKey === key) {
        loading.set(false);
      }
    }
  }

  return {
    data,
    loading,
    error,
    loadMonth,
    injectWorklogIntoCache,
    removeWorklogFromCache,
    refreshDay,
  };
}
