#!/usr/bin/env python3
"""
Real-Time Learning & Adaptation System
Learn from every interaction and improve autonomously
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import traceback

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory


class ReinforcementLearning:
    """
    Learn from outcomes and adapt behavior in real-time

    Features:
    - Track action → outcome pairs
    - Calculate reward signals
    - Update action preferences
    - Explore vs exploit decisions
    - Multi-armed bandit for choices
    - Contextual learning
    """

    def __init__(self, db_path: str = None, learning_rate: float = 0.1):
        workspace = Path(__file__).parent.parent
        if db_path is None:
            db_path = str(workspace / "memory.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

        # Hyperparameters
        self.learning_rate = learning_rate
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.95  # Discount factor for future rewards

        # In-memory cache for fast access
        self.action_values = defaultdict(lambda: {'q_value': 0.0, 'count': 0})
        self._load_action_values()

        # Load Telegram notifier
        try:
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
        except Exception as e:
            print(f"[WARNING] Could not load Telegram notifier: {e}")
            self.notifier = None

    def _init_db(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()

        # Actions taken
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions_taken (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                action_name TEXT NOT NULL,
                context TEXT,
                parameters TEXT,
                chosen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Outcomes observed
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outcomes_observed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                outcome_type TEXT NOT NULL,
                outcome_value REAL,
                success INTEGER,
                reward REAL,
                details TEXT,
                observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_id) REFERENCES actions_taken(id)
            )
        ''')

        # Action values (Q-values)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_key TEXT UNIQUE NOT NULL,
                q_value REAL DEFAULT 0.0,
                visit_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                total_reward REAL DEFAULT 0.0,
                avg_reward REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Learning episodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_name TEXT NOT NULL,
                state_before TEXT,
                action_taken TEXT,
                state_after TEXT,
                reward REAL,
                success INTEGER,
                learning_applied TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Adaptation log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adaptation_type TEXT NOT NULL,
                what_changed TEXT,
                why_changed TEXT,
                expected_improvement REAL,
                actual_improvement REAL,
                adapted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Performance metrics over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                context TEXT,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def _load_action_values(self):
        """Load action values into memory cache"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT action_key, q_value, visit_count FROM action_values')

        for row in cursor.fetchall():
            self.action_values[row['action_key']] = {
                'q_value': row['q_value'],
                'count': row['visit_count']
            }

    # === ACTION SELECTION ===

    def choose_action(self, action_type: str, available_actions: List[str],
                     context: Dict = None, explore: bool = None) -> str:
        """
        Choose best action using epsilon-greedy strategy

        Args:
            action_type: Type of decision (e.g., "optimization_strategy")
            available_actions: List of possible actions
            context: Current context for contextual bandit
            explore: Force exploration (True) or exploitation (False), or None for epsilon-greedy

        Returns:
            Chosen action name
        """
        if not available_actions:
            raise ValueError("No actions available to choose from")

        # Determine explore vs exploit
        if explore is None:
            import random
            explore = random.random() < self.epsilon

        if explore:
            # Exploration: random choice
            import random
            chosen = random.choice(available_actions)
            reason = "exploration"
        else:
            # Exploitation: choose best known action
            best_action = None
            best_value = float('-inf')

            for action in available_actions:
                action_key = self._make_action_key(action_type, action, context)
                q_value = self.action_values[action_key]['q_value']

                if q_value > best_value:
                    best_value = q_value
                    best_action = action

            chosen = best_action if best_action else available_actions[0]
            reason = f"exploitation (Q={best_value:.3f})"

        # Record action
        action_id = self._record_action(action_type, chosen, context)

        return chosen

    def _record_action(self, action_type: str, action_name: str, context: Dict) -> int:
        """Record action taken"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO actions_taken (action_type, action_name, context)
            VALUES (?, ?, ?)
        ''', (action_type, action_name, json.dumps(context) if context else None))
        self.conn.commit()
        return cursor.lastrowid

    # === LEARNING FROM OUTCOMES ===

    def record_outcome(self, action_type: str, action_name: str,
                      success: bool, outcome_value: float = None,
                      context: Dict = None, details: str = None) -> float:
        """
        Record outcome of action and update learning

        Args:
            action_type: Type of action
            action_name: Specific action taken
            success: Whether action succeeded
            outcome_value: Numeric outcome (e.g., performance improvement)
            context: Context in which action was taken
            details: Additional details

        Returns:
            Calculated reward
        """
        # Calculate reward
        reward = self._calculate_reward(success, outcome_value)

        # Get most recent action of this type
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id FROM actions_taken
            WHERE action_type = ? AND action_name = ?
            ORDER BY chosen_at DESC LIMIT 1
        ''', (action_type, action_name))

        result = cursor.fetchone()
        if result:
            action_id = result['id']

            # Record outcome
            cursor.execute('''
                INSERT INTO outcomes_observed
                (action_id, outcome_type, outcome_value, success, reward, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (action_id, action_type, outcome_value, 1 if success else 0, reward, details))
            self.conn.commit()

        # Update Q-value
        self._update_q_value(action_type, action_name, context, reward, success)

        # Check if significant learning occurred
        if abs(reward) > 0.5:
            self._record_learning_episode(action_type, action_name, context, reward, success)

        return reward

    def _calculate_reward(self, success: bool, outcome_value: float = None) -> float:
        """Calculate reward signal"""
        if outcome_value is not None:
            # Use explicit outcome value
            base_reward = outcome_value
        else:
            # Binary success/failure
            base_reward = 1.0 if success else -0.5

        return base_reward

    def _update_q_value(self, action_type: str, action_name: str,
                       context: Dict, reward: float, success: bool):
        """Update Q-value using Q-learning algorithm"""
        action_key = self._make_action_key(action_type, action_name, context)

        # Get current values
        current = self.action_values[action_key]
        old_q = current['q_value']
        count = current['count']

        # Q-learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
        # Simplified: Q(s,a) = Q(s,a) + α[r - Q(s,a)]
        new_q = old_q + self.learning_rate * (reward - old_q)

        # Update cache
        self.action_values[action_key] = {
            'q_value': new_q,
            'count': count + 1
        }

        # Update database
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO action_values
            (action_key, q_value, visit_count, success_count, total_reward, avg_reward, confidence, last_updated)
            VALUES (?, ?, ?,
                    COALESCE((SELECT success_count FROM action_values WHERE action_key = ?), 0) + ?,
                    COALESCE((SELECT total_reward FROM action_values WHERE action_key = ?), 0) + ?,
                    ?, ?, CURRENT_TIMESTAMP)
        ''', (action_key, new_q, count + 1, action_key, 1 if success else 0,
              action_key, reward, new_q, self._calculate_confidence(count + 1)))
        self.conn.commit()

        # Notify if significant learning
        delta = abs(new_q - old_q)
        if delta > 0.3 and self.notifier and count > 5:
            try:
                self.notifier.send_message(
                    f"Learning Update: {action_name}\n"
                    f"Q-value: {old_q:.2f} -> {new_q:.2f}\n"
                    f"After {count+1} trials",
                    priority="info"
                )
            except:
                pass

    def _make_action_key(self, action_type: str, action_name: str, context: Dict) -> str:
        """Create unique key for action in context"""
        if context:
            # Include key context features
            context_str = "_".join(f"{k}={v}" for k, v in sorted(context.items())[:3])
            return f"{action_type}:{action_name}:{context_str}"
        return f"{action_type}:{action_name}"

    def _calculate_confidence(self, visit_count: int) -> float:
        """Calculate confidence based on visit count"""
        # Confidence increases with more visits, asymptotically approaching 1.0
        return min(1.0, visit_count / (visit_count + 10))

    # === LEARNING EPISODES ===

    def _record_learning_episode(self, action_type: str, action_name: str,
                                 context: Dict, reward: float, success: bool):
        """Record significant learning episode"""
        cursor = self.conn.cursor()

        learning_insight = self._generate_learning_insight(action_type, action_name, reward, success)

        cursor.execute('''
            INSERT INTO learning_episodes
            (episode_name, action_taken, reward, success, learning_applied)
            VALUES (?, ?, ?, ?, ?)
        ''', (f"{action_type}:{action_name}", action_name, reward, 1 if success else 0, learning_insight))
        self.conn.commit()

    def _generate_learning_insight(self, action_type: str, action_name: str,
                                   reward: float, success: bool) -> str:
        """Generate insight from learning episode"""
        if success and reward > 0.5:
            return f"{action_name} works well for {action_type} - reinforcing"
        elif not success:
            return f"{action_name} unsuccessful for {action_type} - reducing preference"
        else:
            return f"Neutral outcome for {action_name}"

    # === ADAPTATION ===

    def adapt_strategy(self, strategy_type: str, why: str,
                      expected_improvement: float = None) -> Dict:
        """
        Adapt a strategy based on learning

        Args:
            strategy_type: Type of strategy to adapt
            why: Reason for adaptation
            expected_improvement: Expected improvement (0-1)

        Returns:
            Adaptation details
        """
        # Get best performing actions for this strategy type
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT action_key, q_value, visit_count, avg_reward
            FROM action_values
            WHERE action_key LIKE ?
            ORDER BY q_value DESC
            LIMIT 5
        ''', (f"{strategy_type}:%",))

        top_actions = [dict(row) for row in cursor.fetchall()]

        if not top_actions:
            return {'adapted': False, 'reason': 'No learning data available'}

        # Record adaptation
        best_action = top_actions[0]
        cursor.execute('''
            INSERT INTO adaptations
            (adaptation_type, what_changed, why_changed, expected_improvement)
            VALUES (?, ?, ?, ?)
        ''', (strategy_type, best_action['action_key'], why, expected_improvement or 0.0))
        self.conn.commit()

        return {
            'adapted': True,
            'strategy_type': strategy_type,
            'new_preference': best_action['action_key'],
            'q_value': best_action['q_value'],
            'confidence': self._calculate_confidence(best_action['visit_count']),
            'top_actions': top_actions
        }

    # === ANALYTICS ===

    def get_learning_summary(self) -> Dict:
        """Get summary of learning progress"""
        cursor = self.conn.cursor()

        # Total actions and outcomes
        cursor.execute('SELECT COUNT(*) as count FROM actions_taken')
        total_actions = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM outcomes_observed')
        total_outcomes = cursor.fetchone()['count']

        cursor.execute('SELECT AVG(success) as rate FROM outcomes_observed')
        success_rate = cursor.fetchone()['rate'] or 0.0

        cursor.execute('SELECT AVG(reward) as avg FROM outcomes_observed')
        avg_reward = cursor.fetchone()['avg'] or 0.0

        # Top performing actions
        cursor.execute('''
            SELECT action_key, q_value, visit_count, avg_reward
            FROM action_values
            ORDER BY q_value DESC
            LIMIT 10
        ''')
        top_actions = [dict(row) for row in cursor.fetchall()]

        # Recent adaptations
        cursor.execute('''
            SELECT adaptation_type, what_changed, why_changed, adapted_at
            FROM adaptations
            ORDER BY adapted_at DESC
            LIMIT 5
        ''')
        recent_adaptations = [dict(row) for row in cursor.fetchall()]

        # Learning trend
        cursor.execute('''
            SELECT AVG(reward) as avg_reward,
                   DATE(observed_at) as date
            FROM outcomes_observed
            GROUP BY DATE(observed_at)
            ORDER BY date DESC
            LIMIT 7
        ''')
        weekly_trend = [dict(row) for row in cursor.fetchall()]

        return {
            'total_actions': total_actions,
            'total_outcomes': total_outcomes,
            'success_rate': round(success_rate, 3),
            'avg_reward': round(avg_reward, 3),
            'top_actions': top_actions,
            'recent_adaptations': recent_adaptations,
            'weekly_trend': weekly_trend,
            'exploration_rate': self.epsilon,
            'learning_rate': self.learning_rate
        }

    def get_action_recommendations(self, action_type: str, context: Dict = None) -> List[Dict]:
        """Get recommended actions based on learning"""
        cursor = self.conn.cursor()

        # Get actions for this type
        cursor.execute('''
            SELECT action_key, q_value, visit_count, success_count, avg_reward, confidence
            FROM action_values
            WHERE action_key LIKE ?
            ORDER BY q_value DESC
        ''', (f"{action_type}:%",))

        recommendations = []
        for row in cursor.fetchall():
            action_key = row['action_key']
            # Extract action name from key
            parts = action_key.split(':')
            action_name = parts[1] if len(parts) > 1 else action_key

            recommendations.append({
                'action': action_name,
                'q_value': round(row['q_value'], 3),
                'confidence': round(row['confidence'], 3),
                'success_rate': round(row['success_count'] / row['visit_count'], 3) if row['visit_count'] > 0 else 0,
                'trials': row['visit_count'],
                'avg_reward': round(row['avg_reward'], 3)
            })

        return recommendations

    def reset_learning(self, action_type: str = None):
        """Reset learning for specific action type or all"""
        cursor = self.conn.cursor()

        if action_type:
            cursor.execute('DELETE FROM action_values WHERE action_key LIKE ?', (f"{action_type}:%",))
            self.action_values = {k: v for k, v in self.action_values.items()
                                 if not k.startswith(f"{action_type}:")}
        else:
            cursor.execute('DELETE FROM action_values')
            self.action_values.clear()

        self.conn.commit()

    def close(self):
        """Close database connection"""
        self.conn.close()


# === TEST CODE ===

def main():
    """Test reinforcement learning system"""
    print("Testing Reinforcement Learning System")
    print("=" * 70)

    rl = ReinforcementLearning(learning_rate=0.1)

    try:
        # Simulate learning scenario: choosing optimization strategies
        print("\n1. Learning from optimization strategies...")

        strategies = ["strategy_A", "strategy_B", "strategy_C"]

        # Simulate 20 trials where strategy_B is best
        import random
        for trial in range(20):
            # Choose action
            chosen = rl.choose_action("optimization", strategies)

            # Simulate outcome (strategy_B has 80% success, others 40%)
            if chosen == "strategy_B":
                success = random.random() < 0.8
                outcome_value = 0.8 if success else 0.2
            else:
                success = random.random() < 0.4
                outcome_value = 0.4 if success else -0.2

            # Record outcome
            reward = rl.record_outcome("optimization", chosen, success, outcome_value)

            if (trial + 1) % 5 == 0:
                print(f"   Trial {trial + 1}: Chose {chosen}, Success={success}, Reward={reward:.2f}")

        # Get recommendations
        print("\n2. Getting learned recommendations...")
        recommendations = rl.get_action_recommendations("optimization")

        print("   Learned preferences:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['action']}: Q={rec['q_value']:.3f}, "
                  f"Success={rec['success_rate']:.0%}, Trials={rec['trials']}")

        # Adapt strategy based on learning
        print("\n3. Adapting strategy based on learning...")
        adaptation = rl.adapt_strategy(
            "optimization",
            "Learning shows clear preference",
            expected_improvement=0.4
        )

        if adaptation['adapted']:
            print(f"   Adapted to: {adaptation['new_preference']}")
            print(f"   Confidence: {adaptation['confidence']:.0%}")

        # Learning summary
        print("\n4. Learning summary...")
        summary = rl.get_learning_summary()

        print(f"   Total actions: {summary['total_actions']}")
        print(f"   Total outcomes: {summary['total_outcomes']}")
        print(f"   Success rate: {summary['success_rate']:.0%}")
        print(f"   Avg reward: {summary['avg_reward']:.3f}")
        print(f"   Top action: {summary['top_actions'][0]['action_key'] if summary['top_actions'] else 'None'}")

        print(f"\n[OK] Reinforcement Learning System working!")
        print(f"Database: {rl.db_path}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        traceback.print_exc()
    finally:
        rl.close()


if __name__ == "__main__":
    main()
