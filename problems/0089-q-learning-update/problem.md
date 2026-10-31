Apply a sequence of **Q-learning** updates (Watkins, 1989) to a tabular action-value function.

`Q` has shape `(S, A)`. `transitions` is a list of tuples `(s, a, r, s_next, done)`, where `s`, `a` and `s_next` are ints, `r` is a float and `done` is a bool. Process them **in order**. For each one:

$$
y = \begin{cases} r & \text{if done} \\ r + \gamma \max_{a'} Q(s_{\text{next}}, a') & \text{otherwise} \end{cases}
\qquad
Q(s, a) \leftarrow Q(s, a) + \alpha\,\bigl(y - Q(s, a)\bigr)
$$

Each update uses the table as it stands after all the earlier updates.

Return the updated table as a new float array of shape `(S, A)`. Don't modify `Q` in place.

**Constraints**

- `1 <= S <= 50`, `1 <= A <= 8`
- `0 <= len(transitions) <= 2000`
- `0 < alpha <= 1`, `0 <= gamma <= 1`
