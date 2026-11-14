import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  HardHat,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Upload,
  MapPin,
  Send,
  RefreshCw,
  Sparkles,
  ArrowUpRight,
  Flame
} from 'lucide-react';
import { api } from '../../services/api';
import { WorkOrder, WorkOrderStatus, SeverityLevel } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { SeverityBadge } from '../../components/SeverityBadge';
import { Modal } from '../../components/Modal';

export const ContractorDashboard: React.FC = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Submit Repair Modal
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
      console.error('Failed to fetch orders:', err);
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
    setCost('2800');
    setNotes('Excavated loose gravel, leveled with prime coat, compacted with 1-ton vibrating roller.');
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
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-3xl bg-gradient-to-r from-[#14161b] to-[#261f14] border border-amber-500/30 shadow-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
              Contractor Field Operations Console
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">
            Assigned Work Orders & Repair Proof Submissions
          </h1>
          <p className="text-xs text-slate-400 max-w-xl">
            Logged in as <b>{user?.name || 'Ramesh Kumar (Contractor)'}</b>. Manage assigned road defect locations, start on-site repair, and upload field completion photos for municipal closure.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/damage-map"
            className="px-4 py-2.5 rounded-2xl bg-amber-400 hover:bg-amber-300 text-black text-xs font-bold transition-all flex items-center gap-2 shadow-lg"
          >
            <MapPin className="w-4 h-4" />
            <span>Open Navigation Map</span>
          </Link>
          <button
            onClick={fetchOrders}
            disabled={loading}
            className="p-2.5 rounded-2xl bg-[#16181e] border border-white/10 text-slate-300 hover:text-white"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Assigned Tasks</div>
          <div className="text-2xl font-extrabold text-[#00f0ff] mt-1">{assignedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Ready to start repair</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">In Progress On-Site</div>
          <div className="text-2xl font-extrabold text-amber-400 mt-1">{inProgressCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Crews active on road</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Submitted for Review</div>
          <div className="text-2xl font-extrabold text-purple-400 mt-1">{repairedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Awaiting authority sign-off</div>
        </div>

        <div className="p-5 rounded-3xl bg-[#14161b] border border-white/[0.06] shadow-xl">
          <div className="text-xs text-slate-400 font-medium">Repairs Approved & Closed</div>
          <div className="text-2xl font-extrabold text-[#d4f933] mt-1">{closedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Verified road restored</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-[#14161b] border border-white/[0.06] rounded-2xl overflow-x-auto w-fit">
        {['ALL', 'ASSIGNED', 'IN_PROGRESS', 'REPAIRED', 'CLOSED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition-all shrink-0 ${
              filterStatus === st
                ? 'bg-white text-black shadow-md font-bold'
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
          <div className="text-sm font-bold text-white">No Assigned Work Orders</div>
          <div className="text-xs text-slate-400 mt-1">
            There are currently no repair orders in this status category.
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
                className="rounded-3xl border border-white/[0.06] bg-[#14161b] p-5 shadow-xl space-y-4 flex flex-col justify-between"
              >
                <div className="space-y-3">
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
                  </div>

                  {order.proof_image_url && (
                    <div className="rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center relative">
                      <img src={order.proof_image_url} alt="Proof" className="w-full h-full object-contain" />
                      <span className="absolute bottom-2 left-2 text-[10px] bg-black/80 text-[#d4f933] px-2.5 py-1 rounded-xl backdrop-blur-md font-semibold">
                        Uploaded Repair Proof
                      </span>
                    </div>
                  )}
                </div>

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
      <Modal isOpen={repairModalOpen} onClose={() => setRepairModalOpen(false)} title="Submit Completed Road Repair Work">
        <form onSubmit={handleSubmitRepair} className="space-y-4">
          <div className="p-3.5 bg-[#181a20] border border-white/10 rounded-2xl text-xs text-slate-300">
            Submit field proof photo, materials used, and expense log for inspection <b>#{selectedOrder?.inspection_id}</b>.
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Repair Proof Photo (Mandatory)</label>
            <div className="border-2 border-dashed border-white/10 rounded-2xl p-5 text-center hover:bg-white/[0.04] transition-colors">
              {proofPreview ? (
                <div className="space-y-2">
                  <img src={proofPreview} alt="Preview" className="max-h-40 mx-auto rounded-xl object-contain" />
                  <button type="button" onClick={() => { setProofFile(null); setProofPreview(null); }} className="text-xs text-rose-400 hover:underline">
                    Remove Photo
                  </button>
                </div>
              ) : (
                <label className="cursor-pointer block">
                  <Upload className="w-8 h-8 text-slate-500 mx-auto mb-1.5" />
                  <span className="text-xs text-slate-300 font-medium">Click to upload repaired road surface photo</span>
                  <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                </label>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Materials Used</label>
              <input
                type="text"
                required
                value={materials}
                onChange={(e) => setMaterials(e.target.value)}
                placeholder="e.g. Cold mix asphalt 50kg"
                className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Incurred Cost (₹)</label>
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
            <label className="block text-xs font-semibold text-slate-300 mb-1">Contractor Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-xs p-2.5 rounded-xl border border-white/10 bg-[#16181e] text-white focus:outline-none focus:border-[#d4f933]"
            />
          </div>

          {submitError && (
            <div className="text-xs text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
              {submitError}
            </div>
          )}

          <div className="flex justify-end gap-2.5 pt-3">
            <button type="button" onClick={() => setRepairModalOpen(false)} className="px-4 py-2 rounded-xl border border-white/10 text-xs text-slate-300 hover:bg-white/[0.06]">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="px-5 py-2 rounded-xl bg-[#d4f933] hover:bg-[#bef264] text-black font-bold text-xs transition-colors flex items-center gap-1.5 shadow-lg">
              <Send className="w-3.5 h-3.5" /> {submitting ? 'Submitting to Atlas...' : 'Submit Repaired Work'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
