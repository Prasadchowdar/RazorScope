import { useState } from "react";
import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "../hooks/useCrm";
import type { Task } from "../api/crm";

interface Props {
  leadId: string;
}

function formatDate(iso: string | null) {
  if (!iso) return null;
  const d = new Date(iso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = d.getTime() - today.getTime();
  if (diff < 0) return { label: `${iso}`, overdue: true };
  if (diff < 86_400_000) return { label: "Today", overdue: false };
  if (diff < 2 * 86_400_000) return { label: "Tomorrow", overdue: false };
  return { label: iso, overdue: false };
}

export default function TaskList({ leadId }: Props) {
  const tasks = useTasks(leadId);
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDue, setNewDue] = useState("");
  const [newAssignee, setNewAssignee] = useState("");

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await createTask.mutateAsync({
      title: newTitle.trim(),
      lead_id: leadId,
      due_date: newDue || undefined,
      assignee: newAssignee || undefined,
    });
    setNewTitle("");
    setNewDue("");
    setNewAssignee("");
    setAdding(false);
  }

  async function toggleDone(task: Task) {
    await updateTask.mutateAsync({
      taskId: task.id,
      patch: { status: task.status === "done" ? "open" : "done" },
    });
  }

  const openTasks = (tasks.data ?? []).filter((t) => t.status === "open");
  const doneTasks = (tasks.data ?? []).filter((t) => t.status === "done");

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-gray-500 uppercase">Tasks</p>
        <button
          onClick={() => setAdding(true)}
          className="text-xs text-indigo-600 hover:text-indigo-800"
        >
          + Add
        </button>
      </div>

      {adding && (
        <form onSubmit={handleAdd} className="mb-3 p-3 bg-gray-50 rounded-lg space-y-2">
          <input
            autoFocus
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Task title"
            className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
          <div className="flex gap-2">
            <input
              type="date"
              value={newDue}
              onChange={(e) => setNewDue(e.target.value)}
              className="flex-1 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
            <input
              value={newAssignee}
              onChange={(e) => setNewAssignee(e.target.value)}
              placeholder="Assignee"
              className="flex-1 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setAdding(false)} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
            <button
              type="submit"
              disabled={!newTitle.trim() || createTask.isPending}
              className="text-xs px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {createTask.isPending ? "Adding…" : "Add"}
            </button>
          </div>
        </form>
      )}

      {tasks.isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      ) : openTasks.length === 0 && doneTasks.length === 0 ? (
        <p className="text-xs text-gray-400 py-1">No tasks yet.</p>
      ) : (
        <div className="space-y-1.5">
          {openTasks.map((task) => {
            const due = formatDate(task.due_date);
            return (
              <div key={task.id} className="flex items-start gap-2 group">
                <button
                  onClick={() => toggleDone(task)}
                  className="mt-0.5 w-4 h-4 shrink-0 rounded border border-gray-300 hover:border-indigo-400 flex items-center justify-center"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 leading-tight">{task.title}</p>
                  <div className="flex gap-2 mt-0.5 text-xs text-gray-400">
                    {task.assignee && <span>{task.assignee}</span>}
                    {due && (
                      <span className={due.overdue ? "text-red-500 font-medium" : ""}>
                        {due.overdue ? "⚠ " : ""}{due.label}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteTask.mutateAsync(task.id)}
                  className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 text-xs"
                >
                  ×
                </button>
              </div>
            );
          })}

          {doneTasks.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                {doneTasks.length} completed
              </summary>
              <div className="space-y-1 mt-1">
                {doneTasks.map((task) => (
                  <div key={task.id} className="flex items-start gap-2 opacity-50">
                    <button
                      onClick={() => toggleDone(task)}
                      className="mt-0.5 w-4 h-4 shrink-0 rounded border border-gray-300 bg-gray-200 flex items-center justify-center text-xs text-gray-500"
                    >
                      ✓
                    </button>
                    <p className="text-sm text-gray-500 line-through leading-tight">{task.title}</p>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
