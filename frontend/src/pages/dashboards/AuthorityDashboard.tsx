import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  CheckCircle,
  XCircle,
  Edit3,
  HardHat,
  Send,
  RefreshCw,
  Flame,
  FileCheck,
  AlertTriangle,
  Clock,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { api } from '../../services/api';
import {
  InspectionRecord,
  WorkOrder,
  UserProfile,
  WorkOrderPriority
} from '../../types';
import { SeverityBadge } from '../../components/SeverityBadge';
import { Modal } from '../../components/Modal';
import { useAuth } from '../../context/AuthContext';

export const AuthorityDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'verify' | 'review'>('verify');

  // Pending Verifications
  const [pendingList, setPendingList] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<InspectionRecord | null>(null);

  // Dispatch Modal
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [dispatchInspection, setDispatchInspection] = useState<InspectionRecord | null>(null);
  const [workers, setWorkers] = useState<UserProfile[]>([]);
  const [selectedWorkerEmail, setSelectedWorkerEmail] = useState('');
  const [dispatchPriority, setDispatchPriority] = useState<WorkOrderPriority>('HIGH');
  const [dispatchInstructions, setDispatchInstructions] = useState('');
  const [dispatchDeadline, setDispatchDeadline] = useState('');
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);

  // Completed Repairs for Review
  const [repairedOrders, setRepairedOrders] = useState<WorkOrder[]>([]);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedReviewOrder, setSelectedReviewOrder] = useState<WorkOrder | null>(null);
  const [reviewDecision, setReviewDecision] = useState<'CLOSED' | 'IN_PROGRESS'>('CLOSED');
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [pendingData, ordersData, workersData] = await Promise.allSettled([
        api.getPendingVerifications(),
        api.getWorkOrders({ status: 'REPAIRED' }),
        api.getUsers('worker')
      ]);

      if (pendingData.status === 'fulfilled') setPendingList(pendingData.value);
      if (ordersData.status === 'fulfilled') setRepairedOrders(ordersData.value);
      if (workersData.status === 'fulfilled') {
        setWorkers(workersData.value);
        if (workersData.value.length > 0) setSelectedWorkerEmail(workersData.value[0].email);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleVerify = async (record: InspectionRecord) => {
    setActionLoading(true);
    try {
      await api.verifyInspection(record.inspection_id, user?.name || 'Municipal Validator');
      await fetchData();
      openDispatchModal(record);
    } catch {
      alert('Verification failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const openDispatchModal = (record: InspectionRecord) => {
    setDispatchInspection(record);
    setDispatchPriority(record.overall_severity === 'CRITICAL' ? 'EMERGENCY' : 'HIGH');
    setDispatchInstructions('Excavate broken road surface to sound base, apply tack coat, patch with asphalt, compact level.');
    const in48h = new Date(Date.now() + 48 * 3600 * 1000).toISOString().split('T')[0];
    setDispatchDeadline(in48h);
    setDispatchSuccess(null);
    setDispatchModalOpen(true);
  };

  const submitDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchInspection) return;
    setActionLoading(true);
    try {
      const selectedWorker = workers.find(w => w.email === selectedWorkerEmail);
      await api.assignWorkOrder({
        inspection_id: dispatchInspection.inspection_id,
        assigned_worker_email: selectedWorkerEmail || 'worker@roadsentinel.ai',
        assigned_worker_name: selectedWorker?.name || 'Field Contractor',
        assigned_by: user?.name || 'Municipal Authority',
        priority: dispatchPriority,
        instructions: dispatchInstructions,
        deadline: dispatchDeadline
      });
      setDispatchSuccess('Work order successfully dispatched to contractor crew!');
      setTimeout(() => {
        setDispatchModalOpen(false);
        fetchData();
      }, 1200);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to dispatch work order.');
    } finally {
      setActionLoading(false);
    }
  };

  const openReviewModal = (order: WorkOrder, decision: 'CLOSED' | 'IN_PROGRESS') => {
    setSelectedReviewOrder(order);
    setReviewDecision(decision);
    setReviewNotes(
      decision === 'CLOSED'
        ? 'Field repair verified via proof photo. Smooth road profile restored. Work approved.'
        : 'Surface leveling is insufficient. Please apply another layer and compact properly.'
    );
    setReviewModalOpen(true);
  };

  const submitReview = async () => {
    if (!selectedReviewOrder) return;
    setActionLoading(true);
    try {
      await api.reviewWorkOrder(selectedReviewOrder.order_id, {
        status: reviewDecision,
        authority_review_notes: reviewNotes,
        reviewed_by: user?.name || 'Municipal Validator'
      });
      setReviewModalOpen(false);
      await fetchData();
    } catch {
      alert('Review action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#14161b] to-[#1c1a26] border border-[#d4f933]/30 shadow-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#d4f933]/20 text-[#d4f933] border border-[#d4f933]/30">
              Municipal Authority Operations Console
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            AI Hazard Validation & Contractor Dispatch
          </h1>
          <p className="text-xs text-slate-400 max-w-xl">
            Review incoming neural detections from YOLOv8, dispatch prioritized repair orders to contractor crews, and sign off on completed repairs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/damage-map"
            className="px-4 py-2.5 rounded-2xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold transition-all flex items-center gap-2 shadow-lg"
          >
            <Flame className="w-4 h-4 text-black" />
            <span>Open Damage Map</span>
          </Link>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2.5 rounded-2xl bg-[#16181e] border border-white/10 text-slate-300 hover:text-white"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Pending AI Verification</div>
          <div className="text-2xl font-extrabold text-[#d4f933] mt-1">{pendingList.length}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Awaiting QA validation</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Completed Repairs for Review</div>
          <div className="text-2xl font-extrabold text-purple-400 mt-1">{repairedOrders.length}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Proof uploaded by workers</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Active Contractor Crews</div>
          <div className="text-2xl font-extrabold text-[#00f0ff] mt-1">{workers.length > 0 ? workers.length : 3}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Registered in Atlas DB</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">SLA Resolution Rate</div>
          <div className="text-2xl font-extrabold text-[#ff8800] mt-1">94.2%</div>
          <div className="text-[11px] text-slate-500 mt-0.5">On-time road repairs</div>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 p-1 rounded-2xl bg-[#14161b] border border-white/[0.06] w-fit">
        <button
          onClick={() => setActiveTab('verify')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'verify' ? 'bg-white text-black shadow-md' : 'text-slate-400 hover:text-white'
          }`}
        >
          <span>Pending AI Verification</span>
          <span className="px-1.5 py-0.2 rounded-full bg-[#d4f933] text-black text-[10px]">
            {pendingList.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('review')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            activeTab === 'review' ? 'bg-white text-black shadow-md' : 'text-slate-400 hover:text-white'
          }`}
        >
          <span>Review Completed Repairs</span>
          <span className="px-1.5 py-0.2 rounded-full bg-purple-400 text-black text-[10px]">
            {repairedOrders.length}
          </span>
        </button>
      </div>

      {/* TAB 1: PENDING AI VERIFICATION */}
      {activeTab === 'verify' && (
        <>
          {pendingList.length === 0 ? (
            <div className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-12 text-center shadow-xl">
              <CheckCircle className="w-10 h-10 text-[#d4f933] mx-auto mb-3" />
              <div className="text-sm font-bold text-white">Verification Queue is Empty</div>
              <div className="text-xs text-slate-400 mt-1">All AI hazard detections have been verified and dispatched.</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {pendingList.map((r) => (
                <div
                  key={r.inspection_id}
                  className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-5 shadow-xl space-y-4 flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-white">#{r.inspection_id}</span>
                      <SeverityBadge severity={r.overall_severity} />
                    </div>

                    {r.annotated_filename && (
                      <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center">
                        <img src={`/outputs/${r.annotated_filename}`} alt="Defect" className="w-full h-full object-contain" />
                      </div>
                    )}

                    <div className="text-xs space-y-1 text-slate-300">
                      <div className="truncate"><span className="text-slate-500">Location:</span> {r.location}</div>
                      <div><span className="text-slate-500">Defects:</span> <b>{r.final_potholes}</b> Potholes, <b>{r.final_cracks}</b> Cracks</div>
                      <div className="text-[11px] text-slate-500 font-mono">{r.date}</div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-white/[0.06] space-y-2">
                    <button
                      onClick={() => handleVerify(r)}
                      disabled={actionLoading}
                      className="w-full py-2.5 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Verify & Dispatch to Worker
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* TAB 2: REVIEW CONTRACTOR REPAIRS */}
      {activeTab === 'review' && (
        <div className="space-y-4">
          {repairedOrders.length === 0 ? (
            <div className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-12 text-center shadow-xl">
              <FileCheck className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <div className="text-sm font-bold text-white">No Repairs Awaiting Sign-off</div>
              <div className="text-xs text-slate-400 mt-1">Contractor crews have not submitted new repair proofs yet.</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {repairedOrders.map((order) => (
                <div key={order.order_id} className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-5 shadow-xl space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-mono text-xs font-bold text-white">
                        Work Order #{order.order_id}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        Ref: <b>#{order.inspection_id}</b> · {order.location}
                      </div>
                    </div>
                    <SeverityBadge severity={order.severity} />
                  </div>

                  {order.proof_image_url && (
                    <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center relative">
                      <img src={order.proof_image_url} alt="Proof" className="w-full h-full object-contain" />
                      <span className="absolute bottom-2 left-2 text-[10px] bg-black/80 text-[#d4f933] px-2.5 py-1 rounded-xl backdrop-blur-md font-semibold">
                        Contractor Field Proof
                      </span>
                    </div>
                  )}

                  <div className="p-3.5 bg-[#181a20] rounded-2xl border border-white/[0.04] text-xs space-y-1.5 text-slate-300">
                    <div><b>Contractor:</b> {order.assigned_worker_name} ({order.assigned_worker_email})</div>
                    <div><b>Materials Used:</b> {order.repair_materials || 'Standard asphalt mix'}</div>
                    {order.repair_cost && <div><b>Incurred Cost:</b> ₹{order.repair_cost}</div>}
                    {order.repair_notes && <div><b>Worker Notes:</b> {order.repair_notes}</div>}
                  </div>

                  <div className="pt-2 flex items-center gap-2">
                    <button
                      onClick={() => openReviewModal(order, 'CLOSED')}
                      className="flex-1 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold flex items-center justify-center gap-1.5 shadow-md"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Approve & Close Ticket
                    </button>
                    <button
                      onClick={() => openReviewModal(order, 'IN_PROGRESS')}
                      className="px-4 py-2 rounded-xl border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 text-xs font-bold flex items-center gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Request Rework
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* DISPATCH TO CONTRACTOR MODAL */}
      <Modal isOpen={dispatchModalOpen} onClose={() => setDispatchModalOpen(false)} title="Dispatch Work Order to Contractor">
        <form onSubmit={submitDispatch} className="space-y-4">
          <div className="p-3 bg-[#181a20] border border-white/10 rounded-2xl text-xs text-slate-300">
            Dispatching inspection <b>#{dispatchInspection?.inspection_id}</b> ({dispatchInspection?.overall_severity} - {dispatchInspection?.location}).
            Creates a persistent work order in MongoDB Atlas and assigns to the contractor.
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Select Field Contractor</label>
            <select
              value={selectedWorkerEmail}
              onChange={(e) => setSelectedWorkerEmail(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            >
              {workers.length > 0 ? (
                workers.map(w => (
                  <option key={w.email} value={w.email}>
                    {w.name} ({w.email}) — {w.organization || 'Contractor'}
                  </option>
                ))
              ) : (
                <option value="worker@roadsentinel.ai">Ramesh Kumar (worker@roadsentinel.ai)</option>
              )}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Priority</label>
              <select
                value={dispatchPriority}
                onChange={(e) => setDispatchPriority(e.target.value as WorkOrderPriority)}
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              >
                <option value="EMERGENCY">EMERGENCY</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Deadline</label>
              <input
                type="date"
                value={dispatchDeadline}
                onChange={(e) => setDispatchDeadline(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Repair Instructions</label>
            <textarea
              rows={2}
              value={dispatchInstructions}
              onChange={(e) => setDispatchInstructions(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            />
          </div>

          {dispatchSuccess && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              {dispatchSuccess}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setDispatchModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={actionLoading}
              className="px-5 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold transition-all shadow-md flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" /> Dispatch Work Order
            </button>
          </div>
        </form>
      </Modal>

      {/* REVIEW REPAIR MODAL */}
      <Modal isOpen={reviewModalOpen} onClose={() => setReviewModalOpen(false)} title={reviewDecision === 'CLOSED' ? 'Approve Road Repair & Close Ticket' : 'Request Contractor Rework'}>
        <div className="space-y-4">
          <div className="text-xs text-slate-300">
            {reviewDecision === 'CLOSED'
              ? 'Confirm that the contractor’s field repair meets municipal safety criteria. This marks the inspection as completely repaired.'
              : 'Specify rework notes for the contractor crew to return and fix.'}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Feedback / Audit Remarks</label>
            <textarea
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setReviewModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]"
            >
              Cancel
            </button>
            <button
              onClick={submitReview}
              disabled={actionLoading}
              className={`px-5 py-2 rounded-xl font-bold text-xs transition-all shadow-md ${
                reviewDecision === 'CLOSED' ? 'bg-[#d4f933] text-black hover:bg-[#bef264]' : 'bg-rose-600 text-white hover:bg-rose-500'
              }`}
            >
              {reviewDecision === 'CLOSED' ? 'Approve & Close' : 'Send Back for Rework'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
