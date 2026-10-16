"""Protected contract: unrelated work must never block or discard manual speech."""
import json,queue,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from status_button import StatusButton

class ProtectedButtonTests(unittest.TestCase):
    def test_manual_http_can_start_when_all_background_workers_wait_for_manual(self):
        from button_priority import SynthesisInbox,ManualPreemption
        inbox=SynthesisInbox();release=threading.Event()
        started=[threading.Event(),threading.Event()]
        def background(index):started[index].set();release.wait(2);return 'background'
        try:
            for index in range(2):
                with self.assertRaises(ManualPreemption):
                    inbox.response(('normal',index),lambda index=index:background(index),lambda:True)
            for event in started:self.assertTrue(event.wait(1))
            self.assertEqual(inbox.response('manual',lambda:release.set() or 'manual',lambda:False,manual=True),'manual')
        finally:
            release.set();inbox.pool.shutdown(wait=True);inbox.manual_pool.shutdown(wait=True)

    def test_reader_exception_does_not_end_the_watcher(self):
        class Reader:
            def __init__(self,values):self.values=iter(values)
            def read(self):
                value=next(self.values)
                if isinstance(value,Exception):raise value
                return value
            def describe(self):return dict(connected=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'status_button_settings.json').write_text(json.dumps(dict(device=1,button=25,cooldown_seconds=8)))
            readers=iter([Reader([RuntimeError('driver temporarily failed')]),Reader([False,True])])
            events=[]
            button=StatusButton(start=False,root=root,reader_factory=lambda cfg:next(readers),on_event=lambda event,**data:events.append(event))
            with patch('status_button.time.sleep',side_effect=[None,None,StopIteration]):
                with self.assertRaises(StopIteration):button.watch()
            self.assertTrue(button.requested());self.assertIn('button_error',events)

    def test_partial_settings_write_preserves_existing_binding(self):
        class Reader:
            def read(self):return False
            def describe(self):return dict(connected=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'status_button_settings.json'
            path.write_text(json.dumps(dict(device=1,button=25)))
            seen=[]
            button=StatusButton(start=False,root=root,reader_factory=lambda cfg:seen.append(cfg['button']) or Reader())
            previous=button.reader;path.write_text('{');button.poll(1)
            self.assertIs(button.reader,previous)
            path.write_text(json.dumps(dict(device=2,button=7)));button.poll(2)
            self.assertEqual(seen,[25,7]);self.assertEqual(button.cfg['button'],7)

    def test_preempted_synthesis_is_reused_instead_of_duplicate_inference(self):
        from button_priority import SynthesisInbox,ManualPreemption
        inbox=SynthesisInbox();release=threading.Event();calls=[]
        def fetch():calls.append(True);release.wait(2);return 'audio'
        try:
            with self.assertRaises(ManualPreemption):inbox.response('normal',fetch,lambda:True)
            release.set()
            self.assertEqual(inbox.response('normal',fetch,lambda:False),'audio')
            self.assertEqual(len(calls),1)
        finally:release.set();inbox.pool.shutdown(wait=True)

    def test_pending_button_is_not_silently_expired_by_slow_sdk(self):
        button=StatusButton.__new__(StatusButton);button.events=queue.Queue(maxsize=1);button.events.put(1.)
        with patch('status_button.time.monotonic',return_value=61.):self.assertTrue(button.requested())

    def test_manual_request_is_ahead_of_flags_and_ordinary_speech(self):
        from telemetry_announcer import Announcer
        a=Announcer.__new__(Announcer);a.items=queue.PriorityQueue();a.status_pending=False;a.status_lock=threading.Lock()
        a.items.put((0,(0,0),'旗号',False));a.items.put((1,(0,1),'圈速',False))
        with patch('telemetry_announcer.log'):self.assertTrue(a.submit_status('手动状态'))
        self.assertTrue(a.items.get_nowait()[-1])

    def test_reserved_slot_survives_full_background_queue(self):
        from button_priority import SpeechQueue
        q=SpeechQueue(capacity=2)
        q.put_nowait((1,(0,0),'a',False));q.put_nowait((0,(0,1),'b',False))
        with self.assertRaises(queue.Full):q.put_nowait((1,(0,2),'c',False))
        q.put_nowait((-1,(1,3),'manual',True));self.assertTrue(q.get_nowait()[-1])
        self.assertEqual(q.qsize(),2)

    def test_dispatch_works_without_an_sdk_loop(self):
        from button_dispatch import StatusSnapshot,StatusDispatcher
        snapshot=StatusSnapshot();snapshot.update('剩余油量十升。',True)
        button=StatusButton.__new__(StatusButton);button.events=queue.Queue(maxsize=1);button.events.put(time.monotonic())
        delivered=[];dispatcher=StatusDispatcher(button,snapshot,lambda text:delivered.append(text) or True)
        self.assertTrue(dispatcher.step());self.assertEqual(delivered,['剩余油量十升。'])

    def test_stale_snapshot_does_not_invent_current_state(self):
        from button_dispatch import StatusSnapshot
        snapshot=StatusSnapshot();snapshot.update('旧油量十升。',True,now=0)
        self.assertIn('暂未更新',snapshot.read(now=20));self.assertNotIn('十升',snapshot.read(now=20))

    def test_manual_reservation_expires_and_cannot_be_cleared_by_another_owner(self):
        from button_priority import reserve_manual,release_manual,manual_active
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);reserve_manual(root,'new',now=100)
            release_manual(root,'old');self.assertTrue(manual_active(root,now=101))
            self.assertFalse(manual_active(root,now=1000));release_manual(root,'new')
            self.assertFalse(manual_active(root,now=101))

    def test_waiting_manual_inference_goes_before_waiting_background(self):
        from button_priority import PriorityLock
        lock=PriorityLock();order=[];started=threading.Event()
        def normal():
            started.set()
            with lock.hold(False):order.append('normal')
        def manual():
            with lock.hold(True):order.append('manual')
        with lock.hold(False):
            n=threading.Thread(target=normal);n.start();started.wait(1)
            m=threading.Thread(target=manual);m.start()
            deadline=time.monotonic()+1
            while lock.waiting_manual==0 and time.monotonic()<deadline:time.sleep(.001)
        n.join(1);m.join(1);self.assertEqual(order,['manual','normal'])

    def test_old_audio_cancellation_does_not_purge_manual_acknowledgement(self):
        from button_priority import AudioOwner
        owner=AudioOwner();played=[]
        previous=owner.play(lambda:played.append('normal'))
        owner.play(lambda:played.append('manual_ack'))
        owner.stop(previous,lambda:played.append('purge'))
        self.assertEqual(played,['normal','manual_ack'])

if __name__=='__main__':unittest.main()
