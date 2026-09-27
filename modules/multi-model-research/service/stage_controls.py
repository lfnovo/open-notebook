"""One-stage controls. Never change a sibling or the run's pause policy."""
import asyncio
from workflow import ATTENTION, ancestors, now, ready, refresh_status

class StageControls:
    async def skip_stage(self,run_id,stage_id,expected_state):
        """Explicitly omit one settled parallel contribution, never invent a report."""
        from engine import ServiceError
        async with self.lock:
            run=await self.get(run_id);stage=self.stage(run,stage_id)
            self.check_control_snapshot(run,expected_state,stage_id)
            if run['paused'] or run.get('control_state'):
                raise ServiceError('Önce tüm araştırmayı devam ettirin.',409)
            if stage['status'] in ('running','completed','skipped') or stage.get('report') or (run_id,stage_id) in self.tasks:
                raise ServiceError('Yalnız durduğu doğrulanan, raporu olmayan aşama atlanabilir.',409)
            if stage.get('control_state') in ('stopping','stop_failed','cancelled'):
                raise ServiceError('Önce bu aşamanın durdurma durumunu çözün.',409)
            peers=[s for s in run['stages'] if s['round']==stage['round'] and s['id']!='pre_brief_chatgpt']
            if stage['id']=='pre_brief_chatgpt' or len(peers)<2 or not any(s['id']!=stage_id and s['status']=='completed' and s.get('report') for s in peers):
                raise ServiceError('En az bir tamamlanmış paralel rapor gerekli; birleştirme ve son karar atlanamaz.',409)
            if any((s['attempts'] or s.get('report') or s.get('evidence_packet')) and any(p['id']==stage_id for p in ancestors(run,s)) for s in run['stages']):
                raise ServiceError('Sonraki aşamanın girdisi zaten dondurulmuş; araştırma geçmişi değiştirilemez.',409)
            stage['skip']={'by':'user','at':now(),'previous_status':stage['status'],
                'reason':stage.get('error') or 'User chose to continue without this contribution.'}
            stage.update(status='skipped',control_state=None,control_error=None,next_retry_at=None,error=None,finished_at=now())
            refresh_status(run);await self.store.save(run)
        await self.kick(run_id);self.schedule_sync(run_id)
        return await self.get(run_id)

    @staticmethod
    def stage_snapshot(run,stage):
        return {'scope':'stage','run_paused':run['paused'],'run_control_state':run.get('control_state'),
                'stage':[stage['id'],stage['status'],stage['attempts'],stage.get('control_state')]}

    def start_stage_stop(self,run_id,stage_id,target):
        key=(run_id,stage_id)
        if key in self.control_tasks:return
        task=asyncio.create_task(self.finish_stage_stop(run_id,stage_id,target))
        self.control_tasks[key]=task
        task.add_done_callback(lambda _:self.control_tasks.pop(key,None))

    async def finish_stage_stop(self,run_id,stage_id,target):
        from engine import ServiceError
        error=None;run=await self.get(run_id);stage=self.stage(run,stage_id)
        if stage['status']!='completed':
            try:
                if stage['mode']=='account' and stage.get('request_dispatched'):
                    await self.provider.cancel(stage)
                task=self.tasks.get((run_id,stage_id))
                if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
                from segmented_execution import confirm_cancel
                await confirm_cancel(self,run,stage)
            except Exception as exc:
                error=str(exc) if isinstance(exc,ServiceError) else 'Aşama işleminin durduğu doğrulanamadı.'
        async with self.lock:
            run=await self.get(run_id);stage=self.stage(run,stage_id)
            if stage['status']=='completed':stage.update(control_state=None,control_error=None)
            else:stage.update(control_state='stop_failed' if error else target,status='stop_failed' if error else target,
                              control_error=error,next_retry_at=None)
            refresh_status(run);await self.store.save(run)
        self.schedule_sync(run_id)

    async def stage_action(self,run_id,stage_id,action,expected_state=None):
        from engine import ServiceError
        if action=='skip':return await self.skip_stage(run_id,stage_id,expected_state)
        if action not in ('pause','stop','cancel','resume','restore','retry'):raise ServiceError('Bilinmeyen aşama işlemi.')
        async with self.lock:
            run=await self.get(run_id);stage=self.stage(run,stage_id)
            self.check_control_snapshot(run,expected_state,stage_id)
            if run.get('control_state'):raise ServiceError('Önce tüm araştırmanın durdurma durumunu çözün.',409)
            if stage['status'] in ('completed','skipped'):raise ServiceError('Tamamlanan veya atlanan aşama değiştirilmez.',409)
            held=stage.get('control_state')
            if action in ('pause','stop','cancel'):
                if held=='stopping':return run
                if held=='cancelled':raise ServiceError('Vazgeçilen aşama önce geri yüklenmelidir.',409)
                target={'pause':'paused','stop':'stopped','cancel':'cancelled'}[action]
                stage.update(control_state='stopping',control_target=target,next_retry_at=None,control_error=None)
                # Keep active status until cancellation settles; progress remains truthful.
                refresh_status(run);await self.store.save(run)
                self.start_stage_stop(run_id,stage_id,target)
                return run
            if run['paused']:raise ServiceError('Tüm araştırma duraklatılmış. Önce üstteki araştırma kontrolünden devam edin.',409)
            if held in ('stopping','stop_failed'):raise ServiceError('Önce bu aşamanın durduğunu doğrulayın.',409)
            if held=='cancelled' and action!='restore':raise ServiceError('Bu aşama açıkça geri yüklenmelidir.',409)
            if action=='restore' and held!='cancelled':raise ServiceError('Bu aşama vazgeçilmiş değil.',409)
            if stage['status']=='running' or (run_id,stage_id) in self.tasks:raise ServiceError('Bu aşama zaten çalışıyor.',409)
            if action=='retry' and (stage['status'] not in ATTENTION or held):raise ServiceError('Bu aşama tekrar denemeye uygun değil.',409)
            if action=='resume' and held not in ('paused','stopped'):raise ServiceError('Bu aşama duraklatılmış veya durdurulmuş değil.',409)
            if stage['mode']=='import' and action=='retry':raise ServiceError('İçe aktarma görevi otomatik tekrarlanmaz.',409)
            stage.update(control_state=None,control_error=None,error=None,retry_index=0,next_retry_at=None,
                         status=('waiting_input' if stage['mode']=='import' else 'ready') if ready(run,stage) else 'pending')
            refresh_status(run);await self.store.save(run)
        await self.kick(run_id,only=stage_id)
        return await self.get(run_id)
