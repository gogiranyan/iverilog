/*
 * Copyright (c) 2001-2023 Stephen Williams (steve@icarus.com)
 *
 *    This source code is free software; you can redistribute it
 *    and/or modify it in source code form under the terms of the GNU
 *    General Public License as published by the Free Software
 *    Foundation; either version 2 of the License, or (at your option)
 *    any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU General Public License for more details.
 *
 *    You should have received a copy of the GNU General Public License
 *    along with this program; if not, write to the Free Software
 *    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 */

# include  "vvp_priv.h"
# include  <limits.h>
# include  <string.h>
# include  <assert.h>
# include  <stdlib.h>
# include  <stdbool.h>

const unsigned LABEL_NONE = UINT_MAX;
static unsigned break_label = LABEL_NONE;
static unsigned continue_label = LABEL_NONE;

#define PUSH_JUMPS(bl, cl) do {			  \
	    save_break_label = break_label;	  \
	    save_continue_label = continue_label; \
	    break_label = bl;			  \
	    continue_label = cl;		  \
      } while (0)

#define POP_JUMPS do {				  \
	    break_label = save_break_label;	  \
	    continue_label = save_continue_label; \
      } while (0)

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
int show_stmt_break(ivl_statement_t net, ivl_scope_t sscope)
{
      if (break_label == LABEL_NONE) {
	    fprintf(stderr, "vvp.tgt: error: 'break' not in a loop?!\n");
	    return 1;
      }

      fprintf(vvp_out, "    %%jmp T_%u.%u; break\n", thread_count, break_label);
      return 0;
}

int show_stmt_continue(ivl_statement_t net, ivl_scope_t sscope)
{
      if (continue_label == LABEL_NONE) {
	    fprintf(stderr, "vvp.tgt: error: 'continue' not in a loop?!\n");
	    return 1;
      }

      fprintf(stderr, "vvp.tgt: sorry: 'continue' not implemented.\n");
      return 1;
}
#pragma GCC diagnostic pop

int show_stmt_forever(ivl_statement_t net, ivl_scope_t sscope)
{
      int rc = 0;
      ivl_statement_t stmt = ivl_stmt_sub_stmt(net);
      unsigned lab_top = local_count++;
      unsigned lab_out = local_count++;

      show_stmt_file_line(net, "Forever statement.");

      unsigned save_break_label, save_continue_label;
      PUSH_JUMPS(lab_out, lab_top);

      fprintf(vvp_out, "T_%u.%u ;\n", thread_count, lab_top);
      rc += show_statement(stmt, sscope);
      fprintf(vvp_out, "    %%jmp T_%u.%u;\n", thread_count, lab_top);

      fprintf(vvp_out, "T_%u.%u ;\n", thread_count, lab_out);
      POP_JUMPS;

      return rc;
}

int show_stmt_repeat(ivl_statement_t net, ivl_scope_t sscope)
{
      int rc = 0;
      unsigned lab_top = local_count++, lab_out = local_count++;
      ivl_expr_t expr = ivl_stmt_cond_expr(net);
      const char *sign = ivl_expr_signed(expr) ? "s" : "u";

      unsigned save_break_label, save_continue_label;
      PUSH_JUMPS(lab_out, lab_top);

      show_stmt_file_line(net, "Repeat statement.");

	/* Calculate the repeat count onto the top of the vec4 stack. */
      draw_eval_vec4(expr);

	/* Test that 0 < expr, escape if expr <= 0. If the expr is
	   unsigned, then we only need to try to escape if expr==0 as
	   it will never be <0. */
      fprintf(vvp_out, "T_%u.%u %%dup/vec4;\n", thread_count, lab_top);
      fprintf(vvp_out, "    %%pushi/vec4 0, 0, %u;\n", ivl_expr_width(expr));
      fprintf(vvp_out, "    %%cmp/%s;\n", sign);
      if (ivl_expr_signed(expr))
	    fprintf(vvp_out, "    %%jmp/1xz T_%u.%u, 5;\n", thread_count, lab_out);
      fprintf(vvp_out, "    %%jmp/1 T_%u.%u, 4;\n", thread_count, lab_out);
	/* This adds -1 (all ones in 2's complement) to the count. */
      fprintf(vvp_out, "    %%pushi/vec4 1, 0, %u;\n", ivl_expr_width(expr));
      fprintf(vvp_out, "    %%sub;\n");

      rc += show_statement(ivl_stmt_sub_stmt(net), sscope);

      fprintf(vvp_out, "    %%jmp T_%u.%u;\n", thread_count, lab_top);
      fprintf(vvp_out, "T_%u.%u ;\n", thread_count, lab_out);
      fprintf(vvp_out, "    %%pop/vec4 1;\n");

      POP_JUMPS;

      return rc;
}

int show_stmt_while(ivl_statement_t net, ivl_scope_t sscope)
{
      int rc = 0;

      unsigned top_label = local_count++;
      unsigned out_label = local_count++;

      unsigned save_break_label, save_continue_label;
      PUSH_JUMPS(out_label, top_label);

      show_stmt_file_line(net, "While statement.");

	/* Start the loop. The top of the loop starts a basic block
	   because it can be entered from above or from the bottom of
	   the loop. */
      fprintf(vvp_out, "T_%u.%u ;\n", thread_count, top_label);


	/* Draw the evaluation of the condition expression, and test
	   the result. If the expression evaluates to false, then
	   branch to the out label. */
      int use_flag = draw_eval_condition(ivl_stmt_cond_expr(net));
      fprintf(vvp_out, "    %%jmp/0xz T_%u.%u, %d;\n",
	      thread_count, out_label, use_flag);
      clr_flag(use_flag);

	/* Draw the body of the loop. */
      rc += show_statement(ivl_stmt_sub_stmt(net), sscope);

	/* This is the bottom of the loop. branch to the top where the
	   test is repeated, and also draw the out label. */
      fprintf(vvp_out, "    %%jmp T_%u.%u;\n", thread_count, top_label);
      fprintf(vvp_out, "T_%u.%u ;\n", thread_count, out_label);

      POP_JUMPS;
      
      return rc;
}
