"""
定时任务服务模块
使用 APScheduler 实现定时任务调度，支持 Cron 和 Interval 两种触发方式
"""
import asyncio
import json
import os
import subprocess
import uuid
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# 任务文件路径
TASK_FILE = Path(__file__).parent.parent / "data" / "task.json"
TASK_SCRIPT_DIR = Path(__file__).parent.parent / "data" / "tasks"


class ScheduledTask:
    """
    定时任务数据模型
    """

    def __init__(
        self,
        task_id: str,
        name: str,
        user_id: str,
        schedule: dict[str, Any],
        script: str,
        created_at: Optional[str] = None,
        enabled: bool = True,
    ):
        self.id = task_id
        self.name = name
        self.user_id = user_id
        self.schedule = schedule
        self.script = script
        self.script_file = str(TASK_SCRIPT_DIR / f"{task_id}.py")
        self.created_at = created_at or datetime.now().isoformat()
        self.enabled = enabled

    def save_script(self):
        """保存脚本到文件"""
        TASK_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        script_content = self.script.replace("\\n", "\n").replace("\\t", "\t")
        with open(self.script_file, "w", encoding="utf-8") as f:
            f.write(script_content)

    def load_script(self) -> str:
        """从文件加载脚本"""
        if Path(self.script_file).exists():
            with open(self.script_file, "r", encoding="utf-8") as f:
                return f.read()
        return self.script

    def delete_script(self):
        """删除脚本文件"""
        script_path = Path(self.script_file)
        if script_path.exists():
            script_path.unlink()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "schedule": self.schedule,
            "script": self.script,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduledTask":
        """从字典创建"""
        task = cls(
            task_id=data["id"],
            name=data["name"],
            user_id=data["user_id"],
            schedule=data["schedule"],
            script=data.get("script", ""),
            created_at=data.get("created_at"),
            enabled=data.get("enabled", True),
        )
        task.script = task.load_script()
        return task


class SchedulerService:
    """
    定时任务调度服务
    使用单例模式确保全局唯一实例
    """

    _instance: Optional["SchedulerService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.scheduler: Optional[AsyncIOScheduler] = None
        self.tasks: dict[str, ScheduledTask] = {}
        self.result_callback: Optional[Callable] = None
        self._initialized = True

    def set_result_callback(self, callback: Callable[[str, str, str], Any]):
        """
        设置结果回调函数
        回调参数: (user_id, task_name, result)
        """
        self.result_callback = callback

    def _load_tasks(self) -> list[ScheduledTask]:
        """从文件加载任务"""
        if not TASK_FILE.exists():
            return []

        try:
            with open(TASK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] 加载任务失败: {e}")
            return []

    def _save_tasks(self):
        """保存任务到文件"""
        TASK_FILE.parent.mkdir(parents=True, exist_ok=True)

        tasks_list = [task.to_dict() for task in self.tasks.values()]

        with open(TASK_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": tasks_list}, f, ensure_ascii=False, indent=2)

    def _create_trigger(self, schedule: dict[str, Any]):
        """根据 schedule 配置创建 APScheduler 触发器"""
        schedule_type = schedule.get("type", "cron")

        if schedule_type == "cron":
            cron_expr = schedule.get("cron", "0 0 * * *")
            return CronTrigger.from_crontab(cron_expr)

        elif schedule_type == "interval":
            kwargs = {}
            if "seconds" in schedule:
                kwargs["seconds"] = schedule["seconds"]
            if "minutes" in schedule:
                kwargs["minutes"] = schedule["minutes"]
            if "hours" in schedule:
                kwargs["hours"] = schedule["hours"]
            if "days" in schedule:
                kwargs["days"] = schedule["days"]
            return IntervalTrigger(**kwargs)

        raise ValueError(f"不支持的调度类型: {schedule_type}")

    async def validate_script(self, script: str, timeout: int = 10) -> tuple[bool, str]:
        """
        验证脚本是否可以执行

        Args:
            script: 脚本内容
            timeout: 超时时间（秒）

        Returns:
            (是否成功, 结果或错误信息)
        """
        task_id = f"validate_{uuid.uuid4().hex[:8]}"
        temp_script_file = str(TASK_SCRIPT_DIR / f"{task_id}.py")

        try:
            TASK_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
            script_content = script.replace("\\n", "\n").replace("\\t", "\t")

            with open(temp_script_file, "w", encoding="utf-8") as f:
                f.write(script_content)

            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._execute_script_file_sync,
                    temp_script_file,
                ),
                timeout=timeout,
            )

            success = "error" not in result.lower() and "失败" not in result and "Exception" not in result
            return success, result

        except asyncio.TimeoutError:
            return False, f"验证超时 ({timeout}秒)"
        except Exception as e:
            return False, f"验证失败: {str(e)}"
        finally:
            Path(temp_script_file).unlink(missing_ok=True)

    async def _execute_script(self, task_id: str, script: str) -> str:
        """执行脚本并返回结果"""
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                self._execute_script_sync,
                script,
            )
            return result
        except Exception as e:
            return f"执行错误: {str(e)}"

    async def _execute_script_file(self, script_file: str) -> str:
        """执行脚本文件并返回结果"""
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                None,
                self._execute_script_file_sync,
                script_file,
            )
            return result
        except Exception as e:
            return f"执行错误: {str(e)}"

    def _execute_script_file_sync(self, script_file: str) -> str:
        """同步执行脚本文件（在线程池中运行）"""
        process = None
        python_exe = self._get_python_executable()
        try:
            process = subprocess.Popen(
                [python_exe, script_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env=self._get_venv_env(),
            )

            stdout, stderr = process.communicate(timeout=30)

            if stderr:
                return f"[STDERR]\n{stderr}\n[STDOUT]\n{stdout}" if stdout else f"[ERROR]\n{stderr}"

            return stdout if stdout else "脚本执行完成，无输出"

        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            return "执行超时 (30秒)"
        except Exception as e:
            return f"执行失败: {str(e)}"

    def _get_python_executable(self) -> str:
        """获取虚拟环境中的 Python 解释器路径"""
        venv_path = Path(__file__).parent.parent / ".venv" / "Scripts" / "python.exe"
        if venv_path.exists():
            return str(venv_path)
        return "python"

    def _get_venv_env(self) -> dict:
        """获取虚拟环境的环境变量"""
        venv_path = Path(__file__).parent.parent / ".venv"
        venv_scripts = venv_path / "Scripts"

        env = os.environ.copy()

        if venv_scripts.exists():
            env["VIRTUAL_ENV"] = str(venv_path)
            env["PATH"] = str(venv_scripts) + os.pathsep + env.get("PATH", "")

        env["PYTHONIOENCODING"] = "utf-8"

        return env

    def _execute_script_sync(self, script: str) -> str:
        """同步执行脚本（在线程池中运行）"""
        process = None
        python_exe = self._get_python_executable()
        try:
            process = subprocess.Popen(
                [python_exe, "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env=self._get_venv_env(),
            )

            stdout, stderr = process.communicate(timeout=30)

            if stderr:
                return f"[STDERR]\n{stderr}\n[STDOUT]\n{stdout}" if stdout else f"[ERROR]\n{stderr}"

            return stdout if stdout else "脚本执行完成，无输出"

        except subprocess.TimeoutExpired:
            if process:
                process.kill()
            return "执行超时 (30秒)"
        except Exception as e:
            return f"执行失败: {str(e)}"

    async def _run_task(self, task_id: str):
        """执行定时任务"""
        task = self.tasks.get(task_id)
        if not task:
            print(f"[WARN] 任务不存在: {task_id}")
            return

        if not task.enabled:
            print(f"[INFO] 任务已禁用，跳过执行: {task.name}")
            return

        print(f"[INFO] 开始执行任务: {task.name} (ID: {task.id})")

        result = await self._execute_script_file(task.script_file)

        print(f"[INFO] 任务执行完成: {task.name}, 结果长度: {len(result)} 字符")

        # 条件判断：只有脚本输出了有意义的内容时才发送消息
        # 排除空输出、纯空白、无输出提示等情况
        should_send = self._should_send_message(result)
        
        if not should_send:
            print(f"[INFO] 条件未满足，不发送消息: {task.name}")
            return

        if self.result_callback:
            try:
                await self.result_callback(task.user_id, task.name, result)
                print(f"[INFO] 结果推送成功: {task.name}")
            except Exception as e:
                print(f"[ERROR] 回调执行失败: {e}")

    def _should_send_message(self, result: str) -> bool:
        """
        判断是否应该发送消息
        
        只有脚本输出了有意义的内容时才返回 True
        """
        if not result:
            return False
        
        # 去除首尾空白后检查
        cleaned = result.strip()
        
        # 空字符串
        if not cleaned:
            return False
        
        # 默认的无输出提示
        if cleaned in ["脚本执行完成，无输出", "无"]:
            return False
        
        return True

    async def start(self):
        """启动调度器"""
        if self.scheduler and self.scheduler.running:
            return

        jobstores = {"default": MemoryJobStore()}
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {"coalesce": False, "max_instances": 1}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Asia/Shanghai",
        )

        # 加载已有任务
        saved_tasks = self._load_tasks()
        for task in saved_tasks:
            await self.add_task(task)

        self.scheduler.start()
        print(f"[OK] 调度器已启动，共加载 {len(self.tasks)} 个任务")

    async def stop(self):
        """停止调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            print("[OK] 调度器已停止")

    async def add_task(self, task: ScheduledTask) -> str:
        """添加新任务"""
        if task.id in self.tasks:
            raise ValueError(f"任务 ID 已存在: {task.id}")

        task.save_script()
        self.tasks[task.id] = task
        self._save_tasks()

        if self.scheduler and task.enabled:
            trigger = self._create_trigger(task.schedule)
            self.scheduler.add_job(
                partial(self._run_task, task.id),
                trigger=trigger,
                id=task.id,
                name=task.name,
                replace_existing=True,
            )

        return task.id

    async def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks.pop(task_id)
        task.delete_script()
        self._save_tasks()

        if self.scheduler:
            self.scheduler.remove_job(task_id)

        return True

    async def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.enabled = True
        self._save_tasks()

        if self.scheduler:
            trigger = self._create_trigger(task.schedule)
            self.scheduler.add_job(
                partial(self._run_task, task.id),
                trigger=trigger,
                id=task.id,
                name=task.name,
                replace_existing=True,
            )

        return True

    async def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.enabled = False
        self._save_tasks()

        if self.scheduler:
            self.scheduler.remove_job(task_id)

        return True

    def get_tasks(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        """获取任务列表"""
        tasks = self.tasks.values()

        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]

        return [t.to_dict() for t in tasks]

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """获取单个任务"""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None


# 全局单例实例
scheduler_service = SchedulerService()
