import React, { useEffect, useState } from 'react';
import {
  HardHat,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Calendar,
  MapPin,
  FileCheck,
  Send,
  RefreshCw,
  Sparkles,
  Info,
  ArrowUpRight
} from 'lucide-react';

import { api } from '../services/api';
import { WorkOrder, WorkOrderStatus, SeverityLevel } from '../types';
import { useAuth } from '../context/AuthContext';
import { SeverityBadge } from '../components/SeverityBadge';
import { Modal } from '../components/Modal';

export const WorkerPortal: React.FC = () => {
  const { user, role, loginAs } = useAuth();
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Repair Submission Modal
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null);
  const [repairModalOpen, setRepairModalOpen] = useState(false);
  const [proofFile, setProofFile] = useState<File | null>(null);
  const [proofPreview, setProofPreview] = useState<string | null>(null);
  const [materials, setMaterials] = useState('');
  const [cost, setCost] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const data = await api.getWorkOrders();
      setOrders(data);
    } catch (err) {
      console.error('Failed to fetch work orders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleStartWork = async (orderId: string) => {
    try {
      await api.updateWorkOrderStatus(orderId, { status: 'IN_PROGRESS' });
      await fetchOrders();
    } catch (err) {
      alert('Failed to update status to IN_PROGRESS');
    }
  };

  const openRepairModal = (order: WorkOrder) => {
    setSelectedOrder(order);
    setProofFile(null);
    setProofPreview(null);
    setMaterials('Asphalt cold mix 50kg, cationic bitumen tack coat');
    setCost('2500');
    setNotes('Excavated loose gravel, applied primer tack coat, compacted patch level with road surface.');
    setSubmitError(null);
    setRepairModalOpen(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setProofFile(f);
      setProofPreview(URL.createObjectURL(f));
    }
  };

  const handleSubmitRepair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setSubmitting(true);
    setSubmitError(null);

    try {
      let uploadedProofUrl = '';
      if (proofFile) {
        const formData = new FormData();
        formData.append('file', proofFile);
        const uploadRes = await api.uploadProofPhoto(formData);
        uploadedProofUrl = uploadRes.proof_image_url;
      }

      await api.updateWorkOrderStatus(selectedOrder.order_id, {
        status: 'REPAIRED',
        repair_materials: materials,
        repair_cost: cost ? parseFloat(cost) : undefined,
        repair_notes: notes,
        proof_image_url: uploadedProofUrl || undefined
      });

      setRepairModalOpen(false);
      await fetchOrders();
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || 'Failed to submit repair proof');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredOrders = filterStatus === 'ALL'
    ? orders
    : orders.filter(o => o.status === filterStatus);

  const assignedCount = orders.filter(o => o.status === 'ASSIGNED').length;
  const inProgressCount = orders.filter(o => o.status === 'IN_PROGRESS').length;
  const repairedCount = orders.filter(o => o.status === 'REPAIRED').length;
  const closedCount = orders.filter(o => o.status === 'CLOSED').length;

  return (
    <div className="space-y-6">
      {/* Role Banner if not field worker */}
      {role !== 'worker' && (
        <div className="p-4 rounded-3xl border border-amber-500/20 bg-amber-500/10 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 shrink-0 text-amber-400" />
            <span>
              You are currently viewing as <b>{user?.name}</b> ({role}). Switch to the <b>Field Contractor</b> persona for live road repair actions.
            </span>
          </div>
          <button
            onClick={() => loginAs('worker')}
            className="px-3.5 py-1.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-black font-bold shrink-0 ml-3 transition-colors shadow-md"
          >
            Switch to Contractor
          </button>
        </div>
      )}

      {/* Header & Refresh */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <HardHat className="w-6 h-6 text-[#d4f933]" /> Contractor Operations Portal
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Assigned pothole work orders, on-site telemetry, and photographic repair proof submissions
          </p>
        </div>

        <button
          onClick={fetchOrders}
          disabled={loading}
          className="px-4 py-2 rounded-2xl bg-[#16181e] border border-white/10 text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/[0.06] flex items-center gap-2 transition-all shadow-md"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Orders
        </button>
      </div>

      {/* Metrics Row (Carbon rounded-3xl cards) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Assigned Tasks</div>
          <div className="text-2xl font-extrabold text-[#00f0ff] mt-1">{assignedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Ready for road dispatch</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">In Progress</div>
          <div className="text-2xl font-extrabold text-[#fbbf24] mt-1">{inProgressCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Crews currently on-site</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Under Review</div>
          <div className="text-2xl font-extrabold text-[#a78bfa] mt-1">{repairedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Awaiting authority sign-off</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Repairs Closed</div>
          <div className="text-2xl font-extrabold text-[#d4f933] mt-1">{closedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Completed & verified</div>
        </div>
      </div>

      {/* Status Filter Tabs (Capsules) */}
      <div className="flex items-center gap-1.5 p-1 bg-[#14161b] border border-white/[0.06] rounded-2xl overflow-x-auto">
        {['ALL', 'ASSIGNED', 'IN_PROGRESS', 'REPAIRED', 'CLOSED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition-all shrink-0 ${
              filterStatus === st
                ? 'bg-white text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {st === 'ALL' ? 'All Orders' : st.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Orders Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading work orders from MongoDB Atlas...</div>
      ) : filteredOrders.length === 0 ? (
        <div className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-12 text-center shadow-xl">
          <CheckCircle2 className="w-10 h-10 text-[#d4f933] mx-auto mb-3" />
          <div className="text-sm font-bold text-white">No Work Orders Found</div>
          <div className="text-xs text-slate-400 mt-1">
            There are currently no active repair orders matching the selected filter.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredOrders.map((order) => {
            const isAssigned = order.status === 'ASSIGNED';
            const isInProgress = order.status === 'IN_PROGRESS';
            const isRepaired = order.status === 'REPAIRED';
            const isClosed = order.status === 'CLOSED';

            return (
              <div
                key={order.order_id}
                className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-5 shadow-xl space-y-4 flex flex-col justify-between hover:border-white/10 transition-all"
              >
                <div className="space-y-3">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-white">
                          #{order.order_id}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.06] text-slate-300">
                          Ref: {order.inspection_id}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-300 mt-1 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-[#ff0055] shrink-0" />
                        <span className="truncate">{order.location}</span>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5">
                      <span
                        className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                          isAssigned
                            ? 'bg-[#00f0ff]/20 text-[#00f0ff]'
                            : isInProgress
                            ? 'bg-amber-400/20 text-amber-400'
                            : isRepaired
                            ? 'bg-purple-400/20 text-purple-400'
                            : 'bg-[#d4f933]/20 text-[#d4f933]'
                        }`}
                      >
                        {order.status}
                      </span>
                      <SeverityBadge severity={order.severity} />
                    </div>
                  </div>

                  {/* Details box */}
                  <div className="p-3.5 rounded-2xl bg-[#181a20] border border-white/[0.04] text-xs space-y-2">
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Priority: <b className="text-[#ff0055]">{order.priority}</b></span>
                      <span>Target: {order.deadline || 'ASAP (48h)'}</span>
                    </div>
                    {order.instructions && (
                      <div className="text-slate-300 pt-1.5 border-t border-white/[0.04]">
                        <span className="font-semibold text-slate-400">Instructions:</span> {order.instructions}
                      </div>
                    )}
                    {order.assigned_worker_name && (
                      <div className="text-[11px] text-slate-400">
                        Assigned To: <b className="text-slate-200">{order.assigned_worker_name}</b> ({order.assigned_worker_email})
                      </div>
                    )}
                  </div>

                  {/* Proof Photo Preview if available */}
                  {order.proof_image_url && (
                    <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center relative">
                      <img
                        src={order.proof_image_url}
                        alt="Repair proof"
                        className="w-full h-full object-contain"
                      />
                      <span className="absolute bottom-2 left-2 text-[10px] bg-black/80 text-[#d4f933] px-2.5 py-1 rounded-xl backdrop-blur-md font-semibold">
                        Uploaded Field Repair Proof
                      </span>
                    </div>
                  )}

                  {/* Materials & Cost if already repaired */}
                  {isRepaired || isClosed ? (
                    <div className="text-xs space-y-1 bg-[#181a20] p-3 rounded-2xl border border-white/[0.04] text-slate-300">
                      <div><b>Materials:</b> {order.repair_materials || 'Standard asphalt mix'}</div>
                      {order.repair_cost && <div><b>Incurred Cost:</b> ₹{order.repair_cost}</div>}
                      {order.authority_review_notes && (
                        <div className="pt-1.5 border-t border-white/[0.04] text-[11px] text-emerald-400">
                          <b>Authority Feedback:</b> {order.authority_review_notes}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>

                {/* Contractor Actions */}
                <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between">
                  <div className="text-[11px] text-slate-500 font-mono">
                    Dispatched: {order.assigned_at?.split('T')[0] || 'Recent'}
                  </div>

                  {isAssigned && (
                    <button
                      onClick={() => handleStartWork(order.order_id)}
                      className="px-4 py-2 rounded-xl bg-amber-400 hover:bg-amber-300 text-black text-xs font-bold flex items-center gap-1.5 transition-all shadow-md"
                    >
                      <Clock className="w-3.5 h-3.5" /> Start Repair Work
                    </button>
                  )}

                  {isInProgress && (
                    <button
                      onClick={() => openRepairModal(order)}
                      className="px-4 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black text-xs font-bold flex items-center gap-1.5 transition-all shadow-md"
                    >
                      <Upload className="w-3.5 h-3.5" /> Submit Repaired Work
                    </button>
                  )}

                  {isRepaired && (
                    <span className="text-xs font-semibold text-purple-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" /> Awaiting Authority Sign-off
                    </span>
                  )}

                  {isClosed && (
                    <span className="text-xs font-semibold text-[#d4f933] flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Work Approved & Closed
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Submit Repair Proof Modal */}
      <Modal
        isOpen={repairModalOpen}
        onClose={() => setRepairModalOpen(false)}
        title="Submit Completed Road Repair Work"
      >
        <form onSubmit={handleSubmitRepair} className="space-y-4">
          <div className="p-3.5 bg-[#181a20] border border-white/10 rounded-2xl text-xs text-slate-300">
            Submit field proof photo, materials used, and expense log for inspection{' '}
            <b>#{selectedOrder?.inspection_id}</b>. The municipal authority will review and close the ticket.
          </div>

          {/* Proof Photo Upload */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Repair Completion Proof Photo (Mandatory)
            </label>
            <div className="border-2 border-dashed border-white/10 rounded-2xl p-5 text-center hover:bg-white/[0.04] transition-colors">
              {proofPreview ? (
                <div className="space-y-2">
                  <img src={proofPreview} alt="Preview" className="max-h-40 mx-auto rounded-xl object-contain" />
                  <button
                    type="button"
                    onClick={() => { setProofFile(null); setProofPreview(null); }}
                    className="text-xs text-rose-400 hover:underline"
                  >
                    Remove Photo
                  </button>
                </div>
              ) : (
                <label className="cursor-pointer block">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-1.5" />
                  <span className="text-xs text-slate-300 font-medium">
                    Click to upload repaired road surface photo
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Materials Used
              </label>
              <input
                type="text"
                required
                value={materials}
                onChange={(e) => setMaterials(e.target.value)}
                placeholder="e.g. Cold mix asphalt 50kg, tack coat"
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Incurred Repair Cost (₹)
              </label>
              <input
                type="number"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                placeholder="2500"
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Contractor Field Notes
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Describe compaction, surface leveling, and curing conditions..."
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            />
          </div>

          {submitError && (
            <div className="text-xs text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
              {submitError}
            </div>
          )}

          <div className="flex justify-end gap-2.5 pt-3">
            <button
              type="button"
              onClick={() => setRepairModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black font-bold text-xs transition-colors flex items-center gap-1.5 shadow-lg"
            >
              <Send className="w-3.5 h-3.5" /> {submitting ? 'Submitting to Atlas...' : 'Submit Repaired Work'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
