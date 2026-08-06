"""
中国象棋游戏任务
支持双人对战和简单的AI对战
"""

import os
import sys
from typing import Optional, Tuple, List
from enum import Enum


class ChessPiece(Enum):
    """棋子类型"""
    KING = "将/帅"
    ADVISOR = "士/仕"
    ELEPHANT = "象/相"
    HORSE = "馬"
    CHARIOT = "車"
    CANNON = "炮"
    PAWN = "卒/兵"


class ChessColor(Enum):
    """棋子颜色"""
    RED = "红"
    BLACK = "黑"


class ChessPieceInfo:
    """棋子信息"""
    def __init__(self, piece_type: ChessPiece, color: ChessColor):
        self.piece_type = piece_type
        self.color = color
    
    def __str__(self):
        if self.color == ChessColor.RED:
            return self.piece_type.value[1]  # 返回中文字符
        else:
            return self.piece_type.value[0]


class ChessBoard:
    """中国象棋棋盘"""
    
    def __init__(self):
        # 初始化棋盘 9列 x 10行
        self.board: List[List[Optional[ChessPieceInfo]]] = [[None for _ in range(9)] for _ in range(10)]
        self.current_player = ChessColor.RED
        self.game_over = False
        self.winner = None
        self._setup_initial_board()
    
    def _setup_initial_board(self):
        """设置初始棋盘"""
        # 黑方棋子 (上方)
        self.board[0][0] = ChessPieceInfo(ChessPiece.CHARIOT, ChessColor.BLACK)
        self.board[0][1] = ChessPieceInfo(ChessPiece.HORSE, ChessColor.BLACK)
        self.board[0][2] = ChessPieceInfo(ChessPiece.ELEPHANT, ChessColor.BLACK)
        self.board[0][3] = ChessPieceInfo(ChessPiece.ADVISOR, ChessColor.BLACK)
        self.board[0][4] = ChessPieceInfo(ChessPiece.KING, ChessColor.BLACK)
        self.board[0][5] = ChessPieceInfo(ChessPiece.ADVISOR, ChessColor.BLACK)
        self.board[0][6] = ChessPieceInfo(ChessPiece.ELEPHANT, ChessColor.BLACK)
        self.board[0][7] = ChessPieceInfo(ChessPiece.HORSE, ChessColor.BLACK)
        self.board[0][8] = ChessPieceInfo(ChessPiece.CHARIOT, ChessColor.BLACK)
        
        # 黑方炮
        self.board[2][1] = ChessPieceInfo(ChessPiece.CANNON, ChessColor.BLACK)
        self.board[2][7] = ChessPieceInfo(ChessPiece.CANNON, ChessColor.BLACK)
        
        # 黑方卒
        self.board[3][0] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.BLACK)
        self.board[3][2] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.BLACK)
        self.board[3][4] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.BLACK)
        self.board[3][6] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.BLACK)
        self.board[3][8] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.BLACK)
        
        # 红方棋子 (下方)
        self.board[9][0] = ChessPieceInfo(ChessPiece.CHARIOT, ChessColor.RED)
        self.board[9][1] = ChessPieceInfo(ChessPiece.HORSE, ChessColor.RED)
        self.board[9][2] = ChessPieceInfo(ChessPiece.ELEPHANT, ChessColor.RED)
        self.board[9][3] = ChessPieceInfo(ChessPiece.ADVISOR, ChessColor.RED)
        self.board[9][4] = ChessPieceInfo(ChessPiece.KING, ChessColor.RED)
        self.board[9][5] = ChessPieceInfo(ChessPiece.ADVISOR, ChessColor.RED)
        self.board[9][6] = ChessPieceInfo(ChessPiece.ELEPHANT, ChessColor.RED)
        self.board[9][7] = ChessPieceInfo(ChessPiece.HORSE, ChessColor.RED)
        self.board[9][8] = ChessPieceInfo(ChessPiece.CHARIOT, ChessColor.RED)
        
        # 红方炮
        self.board[7][1] = ChessPieceInfo(ChessPiece.CANNON, ChessColor.RED)
        self.board[7][7] = ChessPieceInfo(ChessPiece.CANNON, ChessColor.RED)
        
        # 红方兵
        self.board[6][0] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.RED)
        self.board[6][2] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.RED)
        self.board[6][4] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.RED)
        self.board[6][6] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.RED)
        self.board[6][8] = ChessPieceInfo(ChessPiece.PAWN, ChessColor.RED)
    
    def display(self):
        """显示棋盘"""
        print("\n  0 1 2 3 4 5 6 7 8")
        print("  -------------------")
        for i, row in enumerate(self.board):
            print(f"{i}|", end="")
            for cell in row:
                if cell is None:
                    print("  ", end="")
                else:
                    print(f"{cell} ", end="")
            print()
        print()
    
    def is_valid_position(self, row: int, col: int) -> bool:
        """检查位置是否有效"""
        return 0 <= row < 10 and 0 <= col < 9
    
    def get_piece(self, row: int, col: int) -> Optional[ChessPieceInfo]:
        """获取指定位置的棋子"""
        if self.is_valid_position(row, col):
            return self.board[row][col]
        return None
    
    def move_piece(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """移动棋子"""
        if self.game_over:
            return False
        
        piece = self.get_piece(from_row, from_col)
        if piece is None:
            print("没有找到棋子！")
            return False
        
        if piece.color != self.current_player:
            print("不能移动对方的棋子！")
            return False
        
        target = self.get_piece(to_row, to_col)
        if target is not None and target.color == self.current_player:
            print("不能吃自己的棋子！")
            return False
        
        # 简化的走法验证（可以进一步完善）
        if self._is_valid_move(piece, from_row, from_col, to_row, to_col):
            # 移动棋子
            self.board[to_row][to_col] = piece
            self.board[from_row][from_col] = None
            
            # 检查是否吃掉对方将/帅
            if target and target.piece_type == ChessPiece.KING:
                self.game_over = True
                self.winner = self.current_player
                print(f"\n{'红' if self.current_player == ChessColor.RED else '黑'}方获胜！")
            
            # 切换玩家
            self.current_player = ChessColor.BLACK if self.current_player == ChessColor.RED else ChessColor.RED
            return True
        
        print("不合法的走法！")
        return False
    
    def _is_valid_move(self, piece: ChessPieceInfo, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """验证走法是否合法（简化版）"""
        # 这里只做简单的验证，实际应该根据棋子类型进行详细验证
        # 为了演示，这里允许大部分移动
        
        # 计算移动距离
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        # 车只能走直线
        if piece.piece_type == ChessPiece.CHARIOT:
            return row_diff == 0 or col_diff == 0
        
        # 马走日字
        if piece.piece_type == ChessPiece.HORSE:
            return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)
        
        # 象走田字
        if piece.piece_type == ChessPiece.ELEPHANT:
            return row_diff == 2 and col_diff == 2
        
        # 士走斜线一格
        if piece.piece_type == ChessPiece.ADVISOR:
            return row_diff == 1 and col_diff == 1
        
        # 将/帅走直线一格（在九宫格内）
        if piece.piece_type == ChessPiece.KING:
            if row_diff + col_diff != 1:
                return False
            # 检查是否在九宫格内
            if piece.color == ChessColor.RED:
                return 7 <= to_row <= 9 and 3 <= to_col <= 5
            else:
                return 0 <= to_row <= 2 and 3 <= to_col <= 5
        
        # 炮走直线，吃子需要隔一个
        if piece.piece_type == ChessPiece.CANNON:
            if row_diff != 0 and col_diff != 0:
                return False
            # 如果是吃子，需要中间隔一个棋子
            target = self.get_piece(to_row, to_col)
            if target is not None:
                count = 0
                if row_diff == 0:
                    for c in range(min(from_col, to_col) + 1, max(from_col, to_col)):
                        if self.board[from_row][c] is not None:
                            count += 1
                else:
                    for r in range(min(from_row, to_row) + 1, max(from_row, to_row)):
                        if self.board[r][from_col] is not None:
                            count += 1
                return count == 1
            else:
                return True
        
        # 兵/卒走法
        if piece.piece_type == ChessPiece.PAWN:
            if piece.color == ChessColor.RED:
                # 红方兵只能向前走，过河后可以左右走
                if from_row >= 5:  # 未过河
                    return to_row == from_row - 1 and to_col == from_col
                else:  # 已过河
                    return to_row == from_row - 1 and to_col == from_col
            else:
                # 黑方卒只能向前走，过河后可以左右走
                if from_row <= 4:  # 未过河
                    return to_row == from_row + 1 and to_col == from_col
                else:  # 已过河
                    return to_row == from_row + 1 and to_col == from_col
        
        return True


class ChessGame:
    """中国象棋游戏"""
    
    def __init__(self):
        self.board = ChessBoard()
    
    def parse_position(self, pos: str) -> Optional[Tuple[int, int]]:
        """解析位置字符串，如 '0,1' 或 '01'"""
        try:
            if ',' in pos:
                row, col = pos.split(',')
                return int(row), int(col)
            elif len(pos) == 2:
                return int(pos[0]), int(pos[1])
        except (ValueError, IndexError):
            pass
        return None
    
    def play(self):
        """开始游戏"""
        print("=" * 50)
        print("        中国象棋")
        print("=" * 50)
        print("规则说明：")
        print("- 输入格式：起始位置,目标位置（如：9,4 9,3）")
        print("- 位置坐标：行号(0-9),列号(0-8)")
        print("- 红方先行")
        print("=" * 50)
        
        while not self.board.game_over:
            self.board.display()
            
            current_color = "红" if self.board.current_player == ChessColor.RED else "黑"
            print(f"当前回合：{current_color}方")
            
            move = input("请输入走法（如：9,4 9,3）：").strip()
            
            if move.lower() in ['quit', 'exit', 'q', '退出']:
                print("游戏结束！")
                break
            
            parts = move.split()
            if len(parts) != 2:
                print("输入格式错误！请使用格式：起始位置 目标位置")
                continue
            
            from_pos = self.parse_position(parts[0])
            to_pos = self.parse_position(parts[1])
            
            if from_pos is None or to_pos is None:
                print("位置格式错误！请使用格式：行号,列号")
                continue
            
            from_row, from_col = from_pos
            to_row, to_col = to_pos
            
            if not self.board.move_piece(from_row, from_col, to_row, to_col):
                print("移动失败，请重试！")
        
        if self.board.game_over:
            self.board.display()
            winner = "红" if self.board.winner == ChessColor.RED else "黑"
            print(f"\n游戏结束！{winner}方获胜！")


def main():
    """主函数"""
    game = ChessGame()
    game.play()


if __name__ == "__main__":
    main()
