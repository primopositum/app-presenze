<script lang="ts">
  import { auth } from '$lib/stores/auth';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  import { useUpdateContrattoOre } from '$lib/hooks/useContratto';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import ButtonGradient from '$lib/components/ButtonGradient.svelte';

  let superadmin = false;
  let saving = false;
  let error: string | null = null;
  let updateContratto = useUpdateContrattoOre({ u_id: undefined });
  let profileUser: any = null;

  const emptyPreSet = {
    lun: 0,
    mar: 0,
    mer: 0,
    gio: 0,
    ven: 0
  };

  function toInt(value: number | null | undefined) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }

  function buildPreSet(oreSett?: Array<number | null>) {
    return {
      lun: toInt(oreSett?.[0]),
      mar: toInt(oreSett?.[1]),
      mer: toInt(oreSett?.[2]),
      gio: toInt(oreSett?.[3]),
      ven: toInt(oreSett?.[4])
    };
  }

  let preSet = emptyPreSet;

  $: superadmin = !!$auth.user?.is_superuser;
  $: profileUser = ($timeEntryUser.user as any) ?? ($auth.user as any) ?? null;
  $: if (profileUser) {
    preSet = buildPreSet(profileUser?.contratti?.[0]?.ore_sett) ?? emptyPreSet;
  } else {
    preSet = emptyPreSet;
  }

  $: updateContratto = useUpdateContrattoOre({ u_id: profileUser?.id });

  async function handleUpdateContratto() {
    if (!superadmin || !profileUser?.id) return;
    saving = true;
    error = null;
    try {
      const ore_sett = [preSet.lun, preSet.mar, preSet.mer, preSet.gio, preSet.ven];
      await updateContratto(ore_sett);
    } catch (e: any) {
      error = e?.message || 'Errore aggiornamento contratto';
    } finally {
      saving = false;
    }
  }
  const handleConfirmSet = () => {
    const today = new Date();
    const weekday = today.getDay(); // 0 domenica, 1 lunedi, ...
    const diffToMonday = weekday === 0 ? -6 : 1 - weekday;
    const monday = new Date(today);
    monday.setDate(today.getDate() + diffToMonday);

    const giorni = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'];
    const currentWeek = giorni.reduce((acc, dayLabel, index) => {
      const date = new Date(monday);
      date.setDate(monday.getDate() + index);
      const iso = date.toISOString().split('T')[0];
      acc[iso] = {
        giorno: dayLabel,
        ore: preSet[dayLabel as keyof typeof preSet] ?? 0
      };
      return acc;
    }, {} as Record<string, { giorno: string; ore: number }>);

  }

  const handleConfirmMonth = () => {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth(); // 0-11
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const weekdayMap = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab'];

    const currentMonth = Array.from({ length: daysInMonth }, (_, i) => {
      const date = new Date(year, month, i + 1);
      const dayIndex = date.getDay();
      const dayLabel = weekdayMap[dayIndex] as keyof typeof preSet | 'sab' | 'dom';
      const iso = date.toISOString().split('T')[0];
      const ore = dayLabel in preSet ? preSet[dayLabel as keyof typeof preSet] ?? 0 : 0;
      return { iso, giorno: dayLabel, ore };
    }).reduce((acc, { iso, giorno, ore }) => {
      acc[iso] = { giorno, ore };
      return acc;
    }, {} as Record<string, { giorno: string; ore: number }>);

  }
</script>


    <div class="mt-10 mx-auto p-2 border-3 w-fit bg-blue-100 border-blue-300 rounded-2xl">
    <div class="text-center font-infinity tracking-[3px] mb-4">Pattern settimanale</div>
        <div class="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
        {#each Object.keys(preSet) as key}
          <div class="flex flex-col items-center p-2 rounded gap-2">
            <label class="text-xs sm:text-sm">{key}</label>

            {#if superadmin}
              <input
                type="number"
                bind:value={preSet[key as keyof typeof preSet]}
                class="border-2 border-transparent w-[3.5em] sm:w-[4em] h-[2.5em] pl-2 outline-none overflow-hidden bg-[#FDD395] rounded-lg text-sm
                      transition-all duration-500
                      hover:border-[#4A9DEC] focus:border-[#4A9DEC]
                      hover:shadow-[0px_0px_0px_7px_rgba(74,157,236,0.2)]
                      focus:shadow-[0px_0px_0px_7px_rgba(74,157,236,0.2)]
                      hover:bg-white focus:bg-white"
              />
            {:else}
              <div
                class="w-[3.5em] sm:w-[4em] h-[2.5em] flex items-center justify-center bg-[#FDD395] rounded-lg font-semibold text-sm"
              >
                {preSet[key as keyof typeof preSet]}
              </div>
            {/if}
          </div>
        {/each}
         {#if superadmin}
        <div class="flex flex-wrap items-center justify-center gap-3 mt-4">
          <ButtonGradient
            title="Aggiorna contratto utente"
            buttonText={saving ? 'Salvataggio...' : 'Aggiorna contratto utente'}
            onClick={handleUpdateContratto}
            disabled={saving || !profileUser?.id}
          />
          {#if error}
            <div class="text-red-600 text-sm">{error}</div>
          {/if}
        </div>
      {/if}
    </div>
    <LoaderOverlay show={saving} />

      </div>

     
