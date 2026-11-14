import React, { useEffect, useState } from 'react';
import {
  CheckSquare,
  CheckCircle,
  XCircle,
  Edit3,
  HardHat,
  RefreshCw,
  Send,
  Eye,
  Calendar,
  AlertTriangle,
  FileCheck
} from 'lucide-react';

import { api } from '../services/api';
import {
  InspectionRecord,
  WorkOrder,
  UserProfile,
  WorkOrderPriority,
  SeverityLevel
} from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';

export const VerificationQueue: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'pending' | 'repairs'>('pending');

  // Pending AI Verifications
  const [pendingList, setPendingList] = useState<InspectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<InspectionRecord | null>(null);

  // Reject Modal
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);

  // Correct Modal
  const [correctModalOpen, setCorrectModalOpen] = useState(false);
  const [correctedClass, setCorrectedClass] = useState('Pothole');
  const [correctedSeverity, setCorrectedSeverity] = useState('MODERATE');
  const [correctionNotes, setCorrectionNotes] = useState('');

  // Dispatch to Contractor Modal
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [dispatchInspection, setDispatchInspection] = useState<InspectionRecord | null>(null);
  const [workers, setWorkers] = useState<UserProfile[]>([]);
  const [selectedWorkerEmail, setSelectedWorkerEmail] = useState('');
  const [dispatchPriority, setDispatchPriority] = useState<WorkOrderPriority>('HIGH');
  const [dispatchInstructions, setDispatchInstructions] = useState('');
  const [dispatchDeadline, setDispatchDeadline] = useState('');
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);

  // Review Completed Repairs Tab
  const [repairedOrders, setRepairedOrders] = useState<WorkOrder[]>([]);
  const [selectedReviewOrder, setSelectedReviewOrder] = useState<WorkOrder | null>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<'CLOSED' | 'IN_PROGRESS'>('CLOSED');
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchPending = async () => {
    setLoading(true);
    try {
      const data = await api.getPendingVerifications();
      setPendingList(data);
    } catch (err) {
      console.error('Failed to fetch pending verifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRepairedOrders = async () => {
    try {
      const data = await api.getWorkOrders({ status: 'REPAIRED' });
      setRepairedOrders(data);
    } catch (err) {
      console.error('Failed to fetch repaired orders:', err);
    }
  };

  const fetchWorkers = async () => {
    try {
      const data = await api.getUsers('worker');
      setWorkers(data);
      if (data.length > 0) {
        setSelectedWorkerEmail(data[0].email);
      }
    } catch (err) {
      console.error('Failed to fetch workers:', err);
    }
  };

  useEffect(() => {
    fetchPending();
    fetchRepairedOrders();
    fetchWorkers();
  }, []);

  const handleVerify = async (record: InspectionRecord) => {
    setActionLoading(true);
    try {
      await api.verifyInspection(record.inspection_id, user?.name || 'Municipal Authority');
      await fetchPending();
      // Prompt to dispatch immediately
      openDispatchModal(record);
    } catch (err) {
      alert('Verification action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const openRejectModal = (record: InspectionRecord) => {
    setSelectedRecord(record);
    setRejectionReason('');
    setRejectError(null);
    setRejectModalOpen(true);
  };

  const submitReject = async () => {
    if (!selectedRecord) return;
    if (!rejectionReason.trim() || rejectionReason.trim().length < 3) {
      setRejectError('Please provide a specific rejection reason.');
      return;
    }

    setActionLoading(true);
    try {
      await api.rejectInspection(selectedRecord.inspection_id, rejectionReason.trim(), user?.name || 'Municipal Authority');
      setRejectModalOpen(false);
      await fetchPending();
    } catch (err: any) {
      setRejectError(err.response?.data?.detail || 'Rejection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const openCorrectModal = (record: InspectionRecord) => {
    setSelectedRecord(record);
    setCorrectedClass('Pothole');
    setCorrectedSeverity(record.overall_severity || 'MODERATE');
    setCorrectionNotes('');
    setCorrectModalOpen(true);
  };

  const submitCorrect = async () => {
    if (!selectedRecord) return;
    setActionLoading(true);
    try {
      await api.correctInspection(selectedRecord.inspection_id, {
        corrected_class: correctedClass,
        corrected_severity: correctedSeverity,
        notes: correctionNotes,
        corrected_by: user?.name || 'Municipal Authority'
      });
      setCorrectModalOpen(false);
      await fetchPending();
    } catch (err) {
      alert('Correction update failed.');
    } finally {
      setActionLoading(false);
    }
  };

  // Dispatch work order
  const openDispatchModal = (record: InspectionRecord) => {
    setDispatchInspection(record);
    setDispatchPriority(record.overall_severity === 'CRITICAL' ? 'EMERGENCY' : record.overall_severity === 'SEVERE' ? 'HIGH' : 'MEDIUM');
    setDispatchInstructions('Excavate broken road surface to sound base, apply tack coat, patch with hot/cold mix asphalt, compact level.');
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
        assigned_by: user?.name || 'Municipal Inspector',
        priority: dispatchPriority,
        instructions: dispatchInstructions,
        deadline: dispatchDeadline
      });
      setDispatchSuccess(`Work Order successfully dispatched to ${selectedWorker?.name || selectedWorkerEmail}!`);
      setTimeout(() => {
        setDispatchModalOpen(false);
        fetchRepairedOrders();
      }, 1200);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to dispatch work order.');
    } finally {
      setActionLoading(false);
    }
  };

  // Review completed repair
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
      await fetchRepairedOrders();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Review action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Tab Switcher & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Municipal Authority Console
          </div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-purple-600" /> Verification & Contractor Dispatch
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            <button
              onClick={() => setActiveTab('pending')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === 'pending'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              <span>Pending AI ({pendingList.length})</span>
            </button>
            <button
              onClick={() => { setActiveTab('repairs'); fetchRepairedOrders(); }}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === 'repairs'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              <span>Review Contractor Repairs ({repairedOrders.length})</span>
            </button>
          </div>

          <button
            onClick={() => { fetchPending(); fetchRepairedOrders(); }}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* TAB 1: PENDING AI DETECTIONS */}
      {activeTab === 'pending' && (
        <>
          {pendingList.length === 0 ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
              <div className="text-sm font-semibold text-slate-900 dark:text-white">Verification Queue is Empty</div>
              <div className="text-xs text-slate-500 mt-1">All AI detections have been reviewed or verified.</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {pendingList.map((r) => (
                <div
                  key={r.inspection_id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4 flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">#{r.inspection_id}</span>
                      <SeverityBadge severity={r.overall_severity} />
                    </div>

                    {r.annotated_filename && (
                      <div className="rounded-lg overflow-hidden border border-slate-100 dark:border-slate-800 bg-black aspect-video flex items-center justify-center">
                        <img
                          src={`/outputs/${r.annotated_filename}`}
                          alt="Detection"
                          className="w-full h-full object-contain"
                        />
                      </div>
                    )}

                    <div className="text-xs space-y-1 text-slate-600 dark:text-slate-400">
                      <div className="truncate"><span className="text-slate-400">Location:</span> {r.location}</div>
                      <div><span className="text-slate-400">Defects:</span> <b>{r.final_potholes}</b> potholes, <b>{r.final_cracks}</b> cracks</div>
                      <div><span className="text-slate-400">Model:</span> {r.model_used}</div>
                      <div className="text-[11px] text-slate-400">{r.date}</div>
                    </div>
                  </div>

                  {/* Actions Row */}
                  <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        onClick={() => handleVerify(r)}
                        disabled={actionLoading}
                        className="px-2 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium flex items-center justify-center gap-1 transition-colors"
                      >
                        <CheckCircle className="w-3.5 h-3.5" /> Verify
                      </button>
                      <button
                        onClick={() => openCorrectModal(r)}
                        disabled={actionLoading}
                        className="px-2 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium flex items-center justify-center gap-1 transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" /> Correct
                      </button>
                      <button
                        onClick={() => openRejectModal(r)}
                        disabled={actionLoading}
                        className="px-2 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium flex items-center justify-center gap-1 transition-colors"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Reject
                      </button>
                    </div>

                    <button
                      onClick={() => openDispatchModal(r)}
                      className="w-full px-2 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                    >
                      <HardHat className="w-3.5 h-3.5" /> Dispatch to Contractor
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* TAB 2: REVIEW COMPLETED CONTRACTOR REPAIRS */}
      {activeTab === 'repairs' && (
        <div className="space-y-4">
          {repairedOrders.length === 0 ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center">
              <FileCheck className="w-10 h-10 text-slate-400 mx-auto mb-3" />
              <div className="text-sm font-semibold text-slate-900 dark:text-white">No Repairs Awaiting Review</div>
              <div className="text-xs text-slate-500 mt-1">
                Contractors have not submitted any completed repair proofs yet.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {repairedOrders.map((order) => (
                <div
                  key={order.order_id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                        Work Order #{order.order_id}
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        Inspection Ref: <b>#{order.inspection_id}</b> | {order.location}
                      </div>
                    </div>
                    <SeverityBadge severity={order.severity} />
                  </div>

                  {/* Proof Photo Display */}
                  {order.proof_image_url ? (
                    <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 bg-black aspect-video flex items-center justify-center relative">
                      <img
                        src={order.proof_image_url}
                        alt="Contractor Proof"
                        className="w-full h-full object-contain"
                      />
                      <span className="absolute bottom-2 left-2 text-[10px] bg-black/75 text-emerald-400 px-2 py-0.5 rounded font-medium">
                        ✓ Contractor Submitted Proof
                      </span>
                    </div>
                  ) : (
                    <div className="p-6 bg-slate-100 dark:bg-slate-800 rounded-lg text-center text-xs text-slate-500">
                      No proof photo attached
                    </div>
                  )}

                  {/* Contractor Report Details */}
                  <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-100 dark:border-slate-800 text-xs space-y-1">
                    <div><b>Contractor:</b> {order.assigned_worker_name} ({order.assigned_worker_email})</div>
                    <div><b>Materials Used:</b> {order.repair_materials || 'Standard asphalt mix'}</div>
                    {order.repair_cost && <div><b>Repair Cost:</b> ₹{order.repair_cost}</div>}
                    {order.repair_notes && (
                      <div className="pt-1 text-slate-600 dark:text-slate-300">
                        <b>Worker Notes:</b> {order.repair_notes}
                      </div>
                    )}
                  </div>

                  {/* Authority Review Actions */}
                  <div className="pt-2 flex items-center gap-2">
                    <button
                      onClick={() => openReviewModal(order, 'CLOSED')}
                      className="flex-1 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Approve & Close Ticket
                    </button>
                    <button
                      onClick={() => openReviewModal(order, 'IN_PROGRESS')}
                      className="px-3 py-2 rounded-lg border border-rose-300 dark:border-rose-800 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-xs font-semibold flex items-center gap-1 transition-colors"
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
      <Modal
        isOpen={dispatchModalOpen}
        onClose={() => setDispatchModalOpen(false)}
        title="Dispatch Repair Work Order to Field Contractor"
      >
        <form onSubmit={submitDispatch} className="space-y-4">
          <div className="p-3 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900 rounded-lg text-xs text-purple-900 dark:text-purple-300">
            Dispatching inspection <b>#{dispatchInspection?.inspection_id}</b> ({dispatchInspection?.overall_severity} - {dispatchInspection?.location}).
            Creates a MongoDB work order entry and assigns to field worker.
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Select Field Contractor
            </label>
            <select
              value={selectedWorkerEmail}
              onChange={(e) => setSelectedWorkerEmail(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
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
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Priority Level
              </label>
              <select
                value={dispatchPriority}
                onChange={(e) => setDispatchPriority(e.target.value as WorkOrderPriority)}
                className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="EMERGENCY">EMERGENCY</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Completion Deadline
              </label>
              <input
                type="date"
                value={dispatchDeadline}
                onChange={(e) => setDispatchDeadline(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Field Repair Instructions
            </label>
            <textarea
              rows={3}
              value={dispatchInstructions}
              onChange={(e) => setDispatchInstructions(e.target.value)}
              placeholder="Specify asphalt grade, compaction standards, safety barricades..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>

          {dispatchSuccess && (
            <div className="text-xs text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 p-2.5 rounded-lg font-medium">
              {dispatchSuccess}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setDispatchModalOpen(false)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={actionLoading}
              className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold transition-colors flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" /> Dispatch Work Order
            </button>
          </div>
        </form>
      </Modal>

      {/* AUTHORITY REVIEW MODAL */}
      <Modal
        isOpen={reviewModalOpen}
        onClose={() => setReviewModalOpen(false)}
        title={reviewDecision === 'CLOSED' ? 'Approve Road Repair & Close Ticket' : 'Request Contractor Rework'}
      >
        <div className="space-y-4">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            {reviewDecision === 'CLOSED'
              ? 'Confirm that the contractor’s field repair meets municipal safety criteria. This marks the inspection as completely repaired.'
              : 'Specify rework notes for the contractor crew to return and fix.'}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Authority Review Feedback / Audit Remarks
            </label>
            <textarea
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setReviewModalOpen(false)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={submitReview}
              disabled={actionLoading}
              className={`px-4 py-1.5 rounded-lg text-white text-xs font-semibold transition-colors ${
                reviewDecision === 'CLOSED' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'
              }`}
            >
              {reviewDecision === 'CLOSED' ? 'Approve & Close' : 'Send Back for Rework'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Reject Modal */}
      <Modal isOpen={rejectModalOpen} onClose={() => setRejectModalOpen(false)} title="Reject AI Detection">
        <div className="space-y-4">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Please enter a mandatory justification for rejecting inspection <b>#{selectedRecord?.inspection_id}</b>.
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Rejection Reason</label>
            <textarea
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g. Manhole cover misclassified as pothole; shadow artifact..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-rose-500"
            />
          </div>
          {rejectError && <div className="text-xs text-rose-600">{rejectError}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setRejectModalOpen(false)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={submitReject}
              disabled={actionLoading}
              className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium"
            >
              Confirm Rejection
            </button>
          </div>
        </div>
      </Modal>

      {/* Correct Modal */}
      <Modal isOpen={correctModalOpen} onClose={() => setCorrectModalOpen(false)} title="Correct AI Detection">
        <div className="space-y-4">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Override damage class or visual severity for inspection <b>#{selectedRecord?.inspection_id}</b>.
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Damage Class</label>
              <select
                value={correctedClass}
                onChange={(e) => setCorrectedClass(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="Pothole">Pothole</option>
                <option value="Longitudinal Crack">Longitudinal Crack</option>
                <option value="Transverse Crack">Transverse Crack</option>
                <option value="Alligator Crack">Alligator Crack</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Visual Severity</label>
              <select
                value={correctedSeverity}
                onChange={(e) => setCorrectedSeverity(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="MINOR">MINOR</option>
                <option value="MODERATE">MODERATE</option>
                <option value="SEVERE">SEVERE</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Inspector Notes</label>
            <input
              type="text"
              value={correctionNotes}
              onChange={(e) => setCorrectionNotes(e.target.value)}
              placeholder="e.g. Verified by visual ground assessment..."
              className="w-full text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setCorrectModalOpen(false)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={submitCorrect}
              disabled={actionLoading}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium"
            >
              Apply Correction
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
